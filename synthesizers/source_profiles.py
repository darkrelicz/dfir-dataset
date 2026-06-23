from dataclasses import dataclass
from pathlib import Path


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


SOURCE_PROFILES: dict[str, SourceProfile] = {
    "mitre_attack": SourceProfile(
        source="mitre_attack",
        source_type="ttp_description",
        prompt_template="ttp_description.md",
        categories=(
            "ttp_identification",
            "triage_and_hunting",
            "detection_engineering",
            "report_generation",
            "artifact_analysis",
        ),
    ),
    "sigma_rules": SourceProfile(
        source="sigma_rules",
        source_type="detection_rule",
        prompt_template="detection_rule.md",
        categories=(
            "detection_engineering",
            "ttp_identification",
            "triage_and_hunting",
            "report_generation",
        ),
    ),
    "atomic_red_team": SourceProfile(
        source="atomic_red_team",
        source_type="ttp_description",
        prompt_template="ttp_description.md",
        categories=(
            "ttp_identification",
            "triage_and_hunting",
            "detection_engineering",
            "artifact_analysis",
        ),
    ),
    "cisa_advisories": SourceProfile(
        source="cisa_advisories",
        source_type="threat_advisory",
        prompt_template="threat_advisory.md",
        categories=(
            "triage_and_hunting",
            "report_generation",
            "ttp_identification",
            "detection_engineering",
        ),
    ),
    "volatility3_docs": SourceProfile(
        source="volatility3_docs",
        source_type="tool_documentation",
        prompt_template="tool_documentation.md",
        categories=("artifact_analysis", "triage_and_hunting", "report_generation"),
    ),
    "mitre_atlas": SourceProfile(
        source="mitre_atlas",
        source_type="ttp_description",
        prompt_template="ttp_description.md",
        categories=(
            "ttp_identification",
            "artifact_analysis",
            "triage_and_hunting",
            "report_generation",
        ),
    ),
    "cisa_kev": SourceProfile(
        source="cisa_kev",
        source_type="vulnerability_catalog",
        prompt_template="vulnerability_catalog.md",
        categories=("triage_and_hunting", "report_generation", "ttp_identification"),
    ),
    "kape_files": SourceProfile(
        source="kape_files",
        source_type="artifact_definition",
        prompt_template="artifact_definition.md",
        categories=("artifact_analysis", "triage_and_hunting"),
        thin_source=True,
    ),
    "hayabusa_rules": SourceProfile(
        source="hayabusa_rules",
        source_type="detection_rule",
        prompt_template="detection_rule.md",
        categories=("detection_engineering", "artifact_analysis", "triage_and_hunting"),
    ),
    "lolbas_gtfobins": SourceProfile(
        source="lolbas_gtfobins",
        source_type="abuse_database",
        prompt_template="abuse_database.md",
        categories=("artifact_analysis", "detection_engineering", "ttp_identification"),
    ),
    "forensic_artifacts": SourceProfile(
        source="forensic_artifacts",
        source_type="artifact_definition",
        prompt_template="artifact_definition.md",
        categories=("artifact_analysis", "triage_and_hunting"),
        thin_source=True,
    ),
    "velociraptor_artifacts": SourceProfile(
        source="velociraptor_artifacts",
        source_type="tool_documentation",
        prompt_template="tool_documentation.md",
        categories=("artifact_analysis", "triage_and_hunting", "detection_engineering"),
    ),
    "hijacklibs": SourceProfile(
        source="hijacklibs",
        source_type="abuse_database",
        prompt_template="abuse_database.md",
        categories=("artifact_analysis", "detection_engineering", "ttp_identification"),
        thin_source=True,
    ),
    "loldrivers": SourceProfile(
        source="loldrivers",
        source_type="abuse_database",
        prompt_template="abuse_database.md",
        categories=("artifact_analysis", "ttp_identification", "detection_engineering"),
        thin_source=True,
    ),
    "ossem_data_dicts": SourceProfile(
        source="ossem_data_dicts",
        source_type="artifact_definition",
        prompt_template="artifact_definition.md",
        categories=("artifact_analysis", "detection_engineering"),
        thin_source=True,
    ),
    "cybersec_skills": SourceProfile(
        source="cybersec_skills",
        source_type="practitioner_workflow",
        prompt_template="practitioner_workflow.md",
        categories=("triage_and_hunting", "artifact_analysis", "detection_engineering"),
    ),
}


CONTENT_TYPE_PROFILES: dict[str, ContentTypeProfile] = {
    "abuse_database": ContentTypeProfile(
        content_type="abuse_database",
        max_pairs=2,
        thin_source=True,
    ),
    "artifact_definition": ContentTypeProfile(
        content_type="artifact_definition",
        max_pairs=2,
        thin_source=True,
    ),
    "atomic_test": ContentTypeProfile(
        content_type="atomic_test",
        prompt_template="atomic_test.md",
    ),
    "case_study": ContentTypeProfile(
        content_type="case_study",
        prompt_template="case_study.md",
        max_pairs=3,
    ),
    "event_dictionary": ContentTypeProfile(
        content_type="event_dictionary",
        prompt_template="event_dictionary.md",
        max_pairs=1,
        thin_source=True,
    ),
    "gtfobins_linux_abuse_function": ContentTypeProfile(
        content_type="gtfobins_linux_abuse_function",
        prompt_template="gtfobins_linux_abuse_function.md",
        max_pairs=2,
    ),
    "gtfobins_linux_alias": ContentTypeProfile(
        content_type="gtfobins_linux_alias",
        prompt_template="gtfobins_linux_alias.md",
        max_pairs=1,
        thin_source=True,
    ),
    "hayabusa_rule": ContentTypeProfile(
        content_type="hayabusa_rule",
        prompt_template="hayabusa_rule.md",
    ),
    "lolbas_windows_lolbin": ContentTypeProfile(
        content_type="lolbas_windows_lolbin",
        prompt_template="lolbas_windows_lolbin.md",
        max_pairs=2,
    ),
    "mitigation": ContentTypeProfile(
        content_type="mitigation",
        prompt_template="mitigation.md",
        max_pairs=1,
        thin_source=True,
    ),
    "tool_module": ContentTypeProfile(
        content_type="tool_module",
        prompt_template="tool_module.md",
        max_pairs=2,
        thin_source=True,
    ),
    "tool_plugin": ContentTypeProfile(
        content_type="tool_plugin",
        prompt_template="tool_plugin.md",
    ),
    "velociraptor_client_artifact": ContentTypeProfile(
        content_type="velociraptor_client_artifact",
        prompt_template="velociraptor_artifact.md",
    ),
    "velociraptor_artifact": ContentTypeProfile(
        content_type="velociraptor_artifact",
        prompt_template="velociraptor_artifact.md",
    ),
    "velociraptor_event_artifact": ContentTypeProfile(
        content_type="velociraptor_event_artifact",
        prompt_template="velociraptor_artifact.md",
    ),
    "velociraptor_internal_artifact": ContentTypeProfile(
        content_type="velociraptor_internal_artifact",
        prompt_template="velociraptor_artifact.md",
        max_pairs=1,
        thin_source=True,
    ),
    "velociraptor_notebook": ContentTypeProfile(
        content_type="velociraptor_notebook",
        prompt_template="velociraptor_artifact.md",
        max_pairs=1,
        thin_source=True,
    ),
    "velociraptor_report_template": ContentTypeProfile(
        content_type="velociraptor_report_template",
        prompt_template="velociraptor_artifact.md",
        max_pairs=1,
        thin_source=True,
    ),
    "velociraptor_server_artifact": ContentTypeProfile(
        content_type="velociraptor_server_artifact",
        prompt_template="velociraptor_artifact.md",
    ),
    "velociraptor_vql_artifact": ContentTypeProfile(
        content_type="velociraptor_vql_artifact",
        prompt_template="velociraptor_artifact.md",
    ),
}


# Pilot defaults follow the plan, but ATLAS is capped because the current
# collector yields 262 docs rather than the original ~65 estimate.
DEFAULT_PILOT_TARGETS: dict[str, int] = {
    "mitre_attack": 25,
    "sigma_rules": 25,
    "atomic_red_team": 25,
    "cisa_advisories": 25,
    "volatility3_docs": 10,
    "mitre_atlas": 30,
    "cisa_kev": 10,
    "kape_files": 20,
    "hayabusa_rules": 30,
    "lolbas_gtfobins": 15,
    "forensic_artifacts": 15,
    "velociraptor_artifacts": 10,
    "hijacklibs": 10,
    "loldrivers": 10,
    "ossem_data_dicts": 10,
    "cybersec_skills": 15,
}


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


def source_template_path(source: str, prompt_root: Path) -> Path:
    return prompt_root / "source_types" / profile_for_source(source).prompt_template


def content_template_path(content_type: str, prompt_root: Path) -> Path | None:
    profile = content_profile_for_type(content_type)
    if not profile.prompt_template:
        return None
    return prompt_root / "content_types" / profile.prompt_template
