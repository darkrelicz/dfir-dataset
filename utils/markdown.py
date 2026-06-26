import re
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def parse_yaml_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        frontmatter = {}

    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return frontmatter, match.group(2)
