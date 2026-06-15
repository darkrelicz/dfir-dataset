"""C5: Volatility 3 Documentation Collector.

Clones the volatilityfoundation/volatility3 repository and extracts plugin
documentation from Python docstrings, output schemas, and selected docs.
"""
import ast
import logging
import re
import textwrap
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import git

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument

logger = logging.getLogger(__name__)

DOCUMENTATION_PATHS = (
    "doc/source/basics.rst",
    "doc/source/getting-started-linux-tutorial.rst",
    "doc/source/getting-started-mac-tutorial.rst",
    "doc/source/getting-started-windows-tutorial.rst",
    "doc/source/glossary.rst",
    "doc/source/symbol-tables.rst",
    "doc/source/vol-cli.rst",
    "doc/source/volshell.rst",
)

USER_OPTION_REQUIREMENTS = {
    "BooleanRequirement",
    "BytesRequirement",
    "ChoiceRequirement",
    "FloatRequirement",
    "IntRequirement",
    "ListRequirement",
    "StringRequirement",
    "URIRequirement",
}

class Volatility3DocsCollector(BaseCollector):

    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_path"])
        self.shallow_clone = config.get("shallow_clone", True)

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0

    def _slugify(self, value: str) -> str:
        """Make a stable document-id component from a path or plugin name."""
        return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()

    def _github_url(self, rel_path: str | Path, source_commit: str) -> str:
        """Build a GitHub source URL pinned to the collected commit."""
        path = Path(rel_path).as_posix()
        return (
            "https://github.com/volatilityfoundation/volatility3"
            f"/blob/{source_commit}/{path}"
        )

    def _get_source_commit(self) -> str:
        """Return the cloned repository commit, falling back to the branch."""
        try:
            return git.Repo(self.clone_path).head.commit.hexsha
        except Exception as e:
            self.warnings.append(f"Could not determine Volatility 3 commit: {e}")
            return "develop"

    def _ast_name(self, node: ast.AST) -> str:
        """Return a readable dotted name for an AST expression."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._ast_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        try:
            return ast.unparse(node)
        except Exception:
            return ""

    def _ast_value(self, node: ast.AST) -> Any:
        """Extract a simple value from AST, using source-like text as fallback."""
        try:
            return ast.literal_eval(node)
        except Exception:
            name = self._ast_name(node)
            return name if name else None

    def _is_plugin_class(self, node: ast.ClassDef) -> bool:
        """Check whether a class inherits from PluginInterface."""
        return any(
            (isinstance(base, ast.Attribute) and base.attr == "PluginInterface")
            or (isinstance(base, ast.Name) and base.id == "PluginInterface")
            for base in node.bases
        )

    def _extract_requirement_details(
        self, method_node: ast.FunctionDef
    ) -> list[dict[str, Any]]:
        """Extract requirement constructor arguments from get_requirements."""
        requirements = []
        for call in ast.walk(method_node):
            if not isinstance(call, ast.Call):
                continue

            req_type = self._ast_name(call.func).split(".")[-1]
            if not req_type.endswith("Requirement"):
                continue

            kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg}
            name_node = kwargs.get("name")
            if not name_node:
                continue

            name = self._ast_value(name_node)
            detail: dict[str, Any] = {"name": str(name), "type": req_type}
            for key in (
                "description",
                "optional",
                "default",
                "choices",
                "architectures",
                "version",
                "component",
                "element_type",
            ):
                if key in kwargs:
                    detail[key] = self._ast_value(kwargs[key])
            requirements.append(detail)

        return requirements

    def _parse_treegrid_columns(
        self,
        node: ast.AST,
        assignments: dict[str, list[dict[str, str]]],
    ) -> list[dict[str, str]]:
        """Parse TreeGrid column tuples from a list literal or named assignment."""
        if isinstance(node, ast.Name):
            return assignments.get(node.id, [])

        if not isinstance(node, (ast.List, ast.Tuple)):
            return []

        columns = []
        for item in node.elts:
            if not isinstance(item, (ast.List, ast.Tuple)) or len(item.elts) < 2:
                continue

            column_name = self._ast_value(item.elts[0])
            if column_name is None:
                continue

            columns.append(
                {
                    "name": str(column_name),
                    "type": self._ast_name(item.elts[1]) or "unknown",
                }
            )

        return columns

    def _extract_output_columns(
        self, class_node: ast.ClassDef
    ) -> list[dict[str, str]]:
        """Extract TreeGrid output columns from the plugin run method."""
        run_method = next(
            (
                item
                for item in class_node.body
                if isinstance(item, ast.FunctionDef) and item.name == "run"
            ),
            None,
        )
        if not run_method:
            return []

        assignments: dict[str, list[dict[str, str]]] = {}
        for item in ast.walk(run_method):
            value = None
            targets: list[ast.expr] = []

            if isinstance(item, ast.Assign):
                value = item.value
                targets = list(item.targets)
            elif isinstance(item, ast.AnnAssign):
                value = item.value
                targets = [item.target]

            if value is None:
                continue

            columns = self._parse_treegrid_columns(value, assignments)
            if not columns:
                continue

            for target in targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = columns

        for call in ast.walk(run_method):
            if not isinstance(call, ast.Call):
                continue

            call_name = self._ast_name(call.func)
            if not (call_name == "TreeGrid" or call_name.endswith(".TreeGrid")):
                continue
            if not call.args:
                continue

            columns = self._parse_treegrid_columns(call.args[0], assignments)
            if columns:
                return columns

        return []

    def _extract_plugin_infos(self, py_file: Path) -> list[dict[str, Any]]:
        """Extract all plugin class info from a Python file using AST parsing."""
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError) as e:
            self.warnings.append(f"Cannot parse {py_file}: {e}")
            return []

        plugin_infos = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            if not self._is_plugin_class(node):
                continue

            class_name = node.name
            docstring = ast.get_docstring(node) or ""

            requirement_details: list[dict[str, Any]] = []
            for item in node.body:
                if (
                    isinstance(item, ast.FunctionDef)
                    and item.name == "get_requirements"
                ):
                    requirement_details = self._extract_requirement_details(item)
                    break

            plugin_infos.append(
                {
                    "class_name": class_name,
                    "docstring": docstring,
                    "requirement_details": requirement_details,
                    "output_columns": self._extract_output_columns(node),
                }
            )

        return plugin_infos

    def _determine_os(self, rel_path: str) -> str:
        """Determine OS from the plugin file path."""
        parts = rel_path.lower()
        if "/windows/" in parts or "\\windows\\" in parts:
            return "Windows"
        elif "/linux/" in parts or "\\linux\\" in parts:
            return "Linux"
        elif "/mac/" in parts or "\\mac\\" in parts:
            return "macOS"
        return "Cross-platform"

    def _get_plugin_module_path(self, rel_path: str) -> str:
        """Generate the module path portion of a Volatility plugin name."""
        parts = Path(rel_path).parts
        ignored_parts = ("volatility3", "framework", "plugins", "__init__.py")
        relevant = [p for p in parts if p not in ignored_parts]
        if relevant:
            return ".".join(p.replace(".py", "") for p in relevant)
        return ""

    def _get_plugin_name(self, rel_path: str, class_name: str) -> str:
        """Generate Volatility's module.Class plugin name."""
        module_path = self._get_plugin_module_path(rel_path)
        if module_path:
            return f"{module_path}.{class_name}"
        return class_name

    def _escape_table_value(self, value: Any) -> str:
        """Escape markdown table metacharacters in a compact cell value."""
        return str(value).replace("|", "\\|").replace("\n", " ")

    def _is_user_option(self, requirement: dict[str, Any]) -> bool:
        """Return whether a requirement represents a CLI/plugin option."""
        return requirement["type"] in USER_OPTION_REQUIREMENTS

    def _build_markdown(self, plugin_name: str, info: dict, os_platform: str) -> str:
        """Build markdown documentation for a plugin."""
        class_name = info["class_name"]
        docstring = info["docstring"]
        requirement_details = info["requirement_details"]
        user_options = [req for req in requirement_details if self._is_user_option(req)]
        output_columns = info["output_columns"]

        lines = [
            f"# Volatility 3 Plugin: {plugin_name}",
            "",
            f"**Class**: `{class_name}`",
            f"**Platform**: {os_platform}",
            "",
        ]

        if docstring:
            lines.append("## Description")
            lines.append(textwrap.dedent(docstring).strip())
            lines.append("")

        if output_columns:
            lines.append("## Output Columns")
            lines.append("| Column | Type |")
            lines.append("|---|---|")
            for column in output_columns:
                column_name = self._escape_table_value(column["name"])
                column_type = self._escape_table_value(column["type"])
                lines.append(f"| `{column_name}` | `{column_type}` |")
            lines.append("")

        if user_options:
            lines.append("## Options")
            for req in user_options:
                line = f"- `{req['name']}` ({req['type']})"
                description = req.get("description")
                if description:
                    line += f": {description}"
                details = []
                for key in (
                    "optional",
                    "default",
                    "choices",
                ):
                    if key in req:
                        details.append(f"{key}={self._escape_table_value(req[key])}")
                if details:
                    line += f" [{'; '.join(details)}]"
                lines.append(line)
            lines.append("")

        return self._to_markdown("\n".join(lines))

    def _collect_documentation_docs(
        self, repo_path: Path, source_ref: str
    ) -> list[RawDocument]:
        """Collect selected practitioner-facing README/RST documentation."""
        docs = []
        for rel_doc_path in DOCUMENTATION_PATHS:
            doc_file = repo_path / rel_doc_path
            if not doc_file.exists():
                self.warnings.append(f"Documentation file not found: {doc_file}")
                continue

            try:
                content = doc_file.read_text(encoding="utf-8", errors="replace")
                if len(content.strip()) < 100:
                    continue

                rel_path = doc_file.relative_to(repo_path)
                stem = rel_path.stem.replace("-", " ").replace("_", " ").title()
                rel_slug = self._slugify(str(rel_path.with_suffix("")))
                doc_type = (
                    "readme"
                    if rel_path.name.lower().startswith("readme")
                    else "documentation"
                )
                doc = RawDocument(
                    doc_id=f"vol3-doc-{rel_slug}",
                    source="volatility3_docs",
                    source_url=self._github_url(rel_path, source_ref),
                    title=f"Volatility 3: {stem}",
                    date_collected=date.today(),
                    date_published=None,
                    content_type="tool_documentation",
                    content_markdown=self._to_markdown(content),
                    metadata={
                        "doc_type": doc_type,
                        "file_path": str(rel_path),
                        "source_commit": source_ref,
                    },
                    word_count=self._count_words(content),
                )
                docs.append(doc)
            except Exception as e:
                self.warnings.append(f"Error reading {doc_file}: {e}")

        return docs

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone Volatility 3 repo: {e}")
            self.duration = time() - start_time
            return 0

        source_commit = self._get_source_commit()

        plugins_dir = self.clone_path / "volatility3" / "framework" / "plugins"
        if not plugins_dir.exists():
            self.errors.append(f"Plugins directory not found under {self.clone_path}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []

        # Collect plugin docstrings, requirements, and output schemas.
        for py_file in sorted(plugins_dir.rglob("*.py")):
            if py_file.name == "__init__.py":
                continue

            rel_path = str(py_file.relative_to(self.clone_path))
            os_platform = self._determine_os(rel_path)

            for info in self._extract_plugin_infos(py_file):
                if not (
                    info["docstring"]
                    or info["requirement_details"]
                    or info["output_columns"]
                ):
                    continue

                module_path = self._get_plugin_module_path(rel_path)
                info["module_path"] = module_path
                plugin_name = self._get_plugin_name(rel_path, info["class_name"])

                markdown = self._build_markdown(plugin_name, info, os_platform)

                metadata: dict[str, Any] = {
                    "class_name": info["class_name"],
                    "plugin_name": plugin_name,
                    "module_path": module_path,
                    "os_platform": os_platform,
                    "requirement_details": info["requirement_details"],
                    "output_columns": info["output_columns"],
                    "source_commit": source_commit,
                }

                doc = RawDocument(
                    doc_id=f"vol3-plugin-{self._slugify(plugin_name)}",
                    source="volatility3_docs",
                    source_url=self._github_url(rel_path, source_commit),
                    title=f"Volatility 3: {plugin_name}",
                    date_collected=date.today(),
                    date_published=None,
                    content_type="tool_plugin",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=self._count_words(markdown),
                )
                docs.append(doc)

        # Also collect selected docs
        docs.extend(self._collect_documentation_docs(self.clone_path, source_commit))

        self.doc_count = self._write_documents(docs, self.output_dir, "volatility3_docs")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} Volatility 3 docs in {self.duration:.1f}s")
        return self.doc_count

    def manifest(self) -> CollectionManifest:
        return CollectionManifest(
            collector=self.__class__.__name__,
            version=self.VERSION,
            source_url=self.config["url"],
            collected_at=datetime.now(timezone.utc),
            document_count=self.doc_count,
            errors=self.errors,
            warnings=self.warnings,
            duration_seconds=self.duration,
        )
