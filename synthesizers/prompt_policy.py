from dataclasses import dataclass
from pathlib import Path
from typing import Any

from synthesizers.schemas import Difficulty
from synthesizers.source_profiles import CONTENT_TYPE_PROFILES, SOURCE_PROFILES


DIFFICULTY_ORDER: tuple[Difficulty, ...] = ("junior", "mid", "senior")


@dataclass(frozen=True)
class PromptPolicy:
    difficulty_targets: dict[Difficulty, float]
    category_templates: dict[str, str]

    def category_template(self, category: str) -> str:
        try:
            return self.category_templates[category]
        except KeyError as exc:
            raise KeyError(
                f"No category prompt template configured for {category}"
            ) from exc


def load_prompt_policy(task_config: dict[str, Any], prompt_root: Path) -> PromptPolicy:
    issues: list[str] = []

    try:
        targets = difficulty_targets(task_config)
    except ValueError as exc:
        issues.append(str(exc))
        targets = {}

    categories = task_config.get("categories", {})
    if not isinstance(categories, dict):
        issues.append("configs/task_categories.yaml categories must be a mapping")
        categories = {}

    category_templates = _category_templates(categories, prompt_root, issues)
    _validate_source_templates(category_templates, prompt_root, issues)
    _validate_content_type_templates(prompt_root, issues)

    if issues:
        raise ValueError(
            "Prompt/profile configuration errors: " + "; ".join(issues)
        )

    return PromptPolicy(
        difficulty_targets=targets,
        category_templates=category_templates,
    )


def difficulty_targets(task_config: dict[str, Any]) -> dict[Difficulty, float]:
    distribution = task_config.get("distribution")
    if not isinstance(distribution, dict):
        raise ValueError("configs/task_categories.yaml must define distribution")

    raw_targets = distribution.get("difficulty_targets")
    if not isinstance(raw_targets, dict):
        raise ValueError("configs/task_categories.yaml must define distribution.difficulty_targets")

    targets: dict[Difficulty, float] = {}
    for label in DIFFICULTY_ORDER:
        if label not in raw_targets:
            raise ValueError(f"configs/task_categories.yaml difficulty_targets is missing {label}")
        try:
            weight = float(raw_targets[label])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"difficulty_targets.{label} must be numeric") from exc
        if weight < 0:
            raise ValueError(f"difficulty_targets.{label} must be non-negative")
        targets[label] = weight

    unknown = set(raw_targets) - set(DIFFICULTY_ORDER)
    if unknown:
        labels = ", ".join(sorted(str(label) for label in unknown))
        raise ValueError(f"configs/task_categories.yaml difficulty_targets has unknown label(s): {labels}")
    if sum(targets.values()) <= 0:
        raise ValueError("difficulty_targets must contain at least one positive weight")

    return targets


def _category_templates(categories: dict, prompt_root: Path, issues: list[str]) -> dict[str, str]:
    templates: dict[str, str] = {}

    if not (prompt_root / "base.md").is_file():
        issues.append(f"Missing base prompt template: {prompt_root / 'base.md'}")

    for category, raw_config in categories.items():
        if not isinstance(raw_config, dict):
            issues.append(f"Category config for {category} must be a mapping")
            continue
        template = raw_config.get("prompt_template")
        if not template:
            issues.append(f"Category {category} is missing prompt_template")
            continue
        template = str(template)
        templates[str(category)] = template

        path = prompt_root / "categories" / template
        if not path.is_file():
            issues.append(f"Missing category prompt template for {category}: {path}")

    return templates


def _validate_source_templates(
    category_templates: dict[str, str],
    prompt_root: Path,
    issues: list[str],
) -> None:
    for source, profile in SOURCE_PROFILES.items():
        source_path = prompt_root / "source_types" / profile.prompt_template
        if not source_path.is_file():
            issues.append(f"Missing source prompt template for {source}: {source_path}")
        for category in profile.categories:
            if category not in category_templates:
                issues.append(f"Source profile {source} references unknown category {category}")


def _validate_content_type_templates(prompt_root: Path, issues: list[str]) -> None:
    for content_type, profile in CONTENT_TYPE_PROFILES.items():
        if not profile.prompt_template:
            continue
        path = prompt_root / "content_types" / profile.prompt_template
        if not path.is_file():
            issues.append(f"Missing content-type prompt template for {content_type}: {path}")
