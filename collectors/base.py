import importlib.metadata
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import git
import jsonlines
from tqdm import tqdm

from collectors.schemas import CollectionManifest, RawDocument

__version__ = importlib.metadata.version("dfir-dataset")
logger = logging.getLogger(__name__)

class BaseCollector(ABC):
    """Base class for all source collectors."""
    VERSION: str = __version__

    @abstractmethod
    def collect(self) -> int:
        """Collect documents, write JSONL to output_dir. Returns doc count."""

    @abstractmethod
    def validate(self) -> dict[str, Any]:
        """Validate collected data. Returns validation report."""

    @abstractmethod
    def manifest(self) -> CollectionManifest:
        """Record manifest after each collection. Returns manifest report."""

    def _clone_repo(self, url: str, clone_path: Path, shallow: bool = True) -> Path:
        """Clone a git repo if it doesn't already exist. Returns Path to cloned repo."""
        if clone_path.exists() and any(clone_path.iterdir()):
            logger.info(f"Repo already exists at {clone_path}, skipping clone.")
            return clone_path

        clone_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cloning {url} -> {clone_path} (shallow={shallow})")
        kwargs: dict[str, Any] = {}
        if shallow:
            kwargs["depth"] = 1
        git.Repo.clone_from(url, str(clone_path), **kwargs)
        return clone_path

    def _write_documents(self, docs: list[RawDocument], output_dir: Path, source_name: str) -> int:
        """Write validated documents to JSONL with progress bar."""
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{source_name}.jsonl"
        with jsonlines.open(file_path, mode="w") as writer:
            for doc in tqdm(docs, desc=f"Writing {source_name}"):
                writer.write(doc.model_dump(mode="json"))
        return len(docs)

    def _count_words(self, text: str) -> int:
        """Consistent word counting across collectors."""
        return len(re.findall(r'\b\w+\b', text))

    def _to_markdown(self, text: str) -> str:
        """Normalize content to clean markdown."""
        if not text:
            return ""
        return text.strip()
