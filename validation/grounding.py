import re

GENERAL_KNOWLEDGE_RE = re.compile(r"\[GENERAL KNOWLEDGE\]", re.IGNORECASE)


def has_general_knowledge_tag(text: str) -> bool:
    return bool(GENERAL_KNOWLEDGE_RE.search(text))


def grounding_mismatch_message(grounding: str, response: str) -> str | None:
    has_tag = has_general_knowledge_tag(response)
    if grounding == "source_only" and has_tag:
        return "grounding is source_only but response contains [GENERAL KNOWLEDGE]"
    if grounding == "source_plus_general" and not has_tag:
        return "grounding is source_plus_general but response has no [GENERAL KNOWLEDGE] tags"
    return None
