from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

import git


def repository_url(repo_url: str) -> str:
    return repo_url[:-4] if repo_url.endswith(".git") else repo_url


def github_blob_url(repo_url: str, ref: str, rel_path: str | Path) -> str:
    path = quote(Path(rel_path).as_posix(), safe="/")
    return f"{repository_url(repo_url)}/blob/{ref}/{path}"


def current_commit(
    clone_path: Path | str,
    fallback: str,
    *,
    label: str = "repository",
    on_error: Callable[[str], None] | None = None,
) -> str:
    try:
        return git.Repo(clone_path).head.commit.hexsha
    except Exception as exc:
        if on_error is not None:
            on_error(f"Could not determine {label} commit: {exc}")
        return fallback
