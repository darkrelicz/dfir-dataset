from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utils.io import load_yaml


PROFILE_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "configs" / "source_profiles.yaml"
)


@dataclass(frozen=True)
class SourceProfile:
    source: str
    source_type: str
    prompt_template: str
    categories: tuple[str, ...]
    thin_source: bool = False


@dataclass(frozen=True)
class ContentTypeProfile:
    content_type: str
    prompt_template: str | None = None
    max_pairs: int | None = None
    thin_source: bool = False


def _load_profile_config(path: Path = PROFILE_CONFIG_PATH) -> dict[str, Any]:
    data = load_yaml(path, default={})
    if not isinstance(data, dict):
        raise ValueError(f"Profile config must be a mapping: {path}")
    return data


def _build_source_profiles(config: dict[str, Any]) -> dict[str, SourceProfile]:
    profiles: dict[str, SourceProfile] = {}
    for source, raw_profile in config.items():
        if not isinstance(raw_profile, dict):
            raise ValueError(f"Source profile for {source} must be a mapping")

        try:
            source_type = str(raw_profile["source_type"])
            prompt_template = str(raw_profile["prompt_template"])
            categories = tuple(str(value) for value in raw_profile["categories"])
        except KeyError as exc:
            raise ValueError(f"Source profile for {source} is missing {exc}") from exc

        if not categories:
            raise ValueError(f"Source profile for {source} must define categories")

        profiles[source] = SourceProfile(
            source=source,
            source_type=source_type,
            prompt_template=prompt_template,
            categories=categories,
            thin_source=bool(raw_profile.get("thin_source", False)),
        )
    return profiles


def _build_content_type_profiles(config: dict[str, Any]) -> dict[str, ContentTypeProfile]:
    profiles: dict[str, ContentTypeProfile] = {}
    for content_type, raw_profile in config.items():
        if not isinstance(raw_profile, dict):
            raise ValueError(f"Content-type profile for {content_type} must be a mapping")

        max_pairs = raw_profile.get("max_pairs")
        profiles[content_type] = ContentTypeProfile(
            content_type=content_type,
            prompt_template=raw_profile.get("prompt_template"),
            max_pairs=int(max_pairs) if max_pairs is not None else None,
            thin_source=bool(raw_profile.get("thin_source", False)),
        )
    return profiles


def _build_pilot_targets(config: dict[str, Any]) -> dict[str, int]:
    return {str(source): int(limit) for source, limit in config.items()}


_PROFILE_CONFIG = _load_profile_config()
SOURCE_PROFILES = _build_source_profiles(_PROFILE_CONFIG.get("source_profiles", {}))
CONTENT_TYPE_PROFILES = _build_content_type_profiles(_PROFILE_CONFIG.get("content_type_profiles", {}))
DEFAULT_PILOT_TARGETS = _build_pilot_targets(_PROFILE_CONFIG.get("pilot_targets", {}))


def profile_for_source(source: str) -> SourceProfile:
    try:
        return SOURCE_PROFILES[source]
    except KeyError as exc:
        raise KeyError(f"No synthesis source profile configured for {source}") from exc


def content_profile_for_type(content_type: str) -> ContentTypeProfile:
    return CONTENT_TYPE_PROFILES.get(
        content_type,
        ContentTypeProfile(content_type=content_type),
    )
