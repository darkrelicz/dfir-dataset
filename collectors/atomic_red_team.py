import datetime
import time
from pathlib import Path
from typing import Any

import git
import yaml

from collectors.base import BaseCollector
from collectors.schemas import RawDocument

class AtomicRedTeamCollector(BaseCollector):
    SOURCE_URL = "https://github.com/redcanaryco/atomic-red-team.git"
    LICENSE = "MIT"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.url = config.get("url", self.SOURCE_URL)
        self.clone_dir = Path(config["clone_dir"])
        self.atomics_subdir = config.get("atomics_subdir", "atomics")
        self.platforms = config.get("platforms", ["windows", "linux", "macos"])
        
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.doc_count = 0
        self.duration = 0.0

    def _clone_or_pull(self):
        if self.clone_dir.exists():
            repo = git.Repo(self.clone_dir)
            repo.remotes.origin.pull()
        else:
            self.clone_dir.parent.mkdir(parents=True, exist_ok=True)
            git.Repo.clone_from(self.url, self.clone_dir, depth=1)

    def collect(self, output_dir: Path) -> int:
        start_time = time.time()
        try:
            self._clone_or_pull()
        except Exception as e:
            self.errors.append(f"Failed to clone/pull ART repo: {e}")
            self.duration = time.time() - start_time
            return 0

        atomics_dir = self.clone_dir / self.atomics_subdir
        if not atomics_dir.exists():
            self.errors.append(f"Atomics directory not found: {atomics_dir}")
            self.duration = time.time() - start_time
            return 0

        docs = []
        collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for yml_path in atomics_dir.glob("T*/T*.yaml"):
            try:
                with open(yml_path, "r", encoding="utf-8") as f:
                    technique_data = yaml.safe_load(f)
                    
                if not isinstance(technique_data, dict):
                    self.warnings.append(f"Invalid format in {yml_path.name}")
                    continue
                    
                technique_id = technique_data.get("attack_technique", yml_path.stem)
                atomic_tests = technique_data.get("atomic_tests", [])
                
                for i, test in enumerate(atomic_tests):
                    test_platforms = test.get("supported_platforms", [])
                    
                    has_platform = False
                    for target_plat in self.platforms:
                        if any(target_plat.lower() in p.lower() for p in test_platforms):
                            has_platform = True
                            break
                            
                    if not has_platform and self.platforms:
                        continue
                        
                    test_name = test.get("name", f"Test {i}")
                    doc_id = f"art-{technique_id}-{i}"
                    
                    markdown_lines = [
                        f"# {test_name}",
                        "",
                        f"**Technique:** {technique_id}",
                        f"**Platforms:** {', '.join(test_platforms)}",
                        "",
                        "## Description",
                        str(test.get("description", "No description provided.")),
                        ""
                    ]
                    
                    executor = test.get("executor", {})
                    markdown_lines.append(f"## Executor: {executor.get('name', 'Unknown')}")
                    
                    command = executor.get("command", "")
                    if command:
                        markdown_lines.append("### Command")
                        markdown_lines.append("```")
                        markdown_lines.append(str(command))
                        markdown_lines.append("```")
                        
                    cleanup = executor.get("cleanup_command", "")
                    if cleanup:
                        markdown_lines.append("### Cleanup Command")
                        markdown_lines.append("```")
                        markdown_lines.append(str(cleanup))
                        markdown_lines.append("```")
                        
                    input_args = test.get("input_arguments", {})
                    if input_args:
                        markdown_lines.append("### Input Arguments")
                        for arg_name, arg_details in input_args.items():
                            markdown_lines.append(f"- **{arg_name}**: {arg_details.get('description', '')} (Default: `{arg_details.get('default', '')}`)")
                            
                    content_markdown = self._to_markdown("\n".join(markdown_lines))
                    
                    metadata = {
                        "attack_technique": technique_id,
                        "test_name": test_name,
                        "supported_platforms": test_platforms,
                        "executor_type": executor.get("name", ""),
                        "has_cleanup": bool(cleanup),
                        "input_arguments": list(input_args.keys()) if input_args else [],
                        "dependencies": [d.get("description", "") for d in test.get("dependencies", [])]
                    }
                    
                    doc = RawDocument(
                        doc_id=doc_id,
                        source="atomic_red_team",
                        source_url=f"{self.url.replace('.git', '')}/blob/master/{self.atomics_subdir}/{technique_id}/{yml_path.name}",
                        title=f"{technique_id}: {test_name}",
                        date_collected=collected_at,
                        content_type="atomic_test",
                        content_markdown=content_markdown,
                        metadata=metadata,
                        license=self.LICENSE,
                        word_count=self._count_words(content_markdown)
                    )
                    docs.append(doc)
            except Exception as e:
                self.warnings.append(f"Failed to parse {yml_path.name}: {e}")

        self.doc_count = self._write_documents(docs, output_dir, "atomic_red_team")
        self.duration = time.time() - start_time
        return self.doc_count

    def validate(self, output_dir: Path) -> dict[str, Any]:
        return {}

    def manifest(self) -> dict[str, Any]:
        return {
            "collector": "AtomicRedTeamCollector",
            "version": self.VERSION,
            "source_url": self.url,
            "license": self.LICENSE,
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "document_count": self.doc_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration
        }
