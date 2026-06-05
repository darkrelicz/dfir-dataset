import importlib.metadata
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import jsonlines
from tqdm import tqdm

from collectors.schemas import CollectionManifest, RawDocument

__version__ = importlib.metadata.version("dfir-dataset")

class BaseCollector(ABC):
    """Base class for all source collectors."""
    VERSION: str = __version__
    SOURCE_URL: str

    @abstractmethod
    def collect(self, output_dir: Path) -> int:
        """Collect documents, write JSONL to output_dir. Returns doc count."""

    @abstractmethod
    def validate(self, output_dir: Path) -> dict[str, Any]:
        """Validate collected data. Returns validation report."""

    @abstractmethod
    def manifest(self) -> CollectionManifest:
        """Record manifest after each collection. Returns manifest report."""

    def _write_documents(self, docs: list[RawDocument], output_dir: Path, source_name: str) -> int:
        """Write validated documents to JSONL with progress bar."""
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{source_name}.jsonl"
        with jsonlines.open(file_path, mode="w") as writer:
            for doc in tqdm(docs, desc=f"Writing {source_name}"):
                writer.write(doc.model_dump())
        return len(docs)

    def _count_words(self, text: str) -> int:
        """Consistent word counting across collectors."""
        return len(re.findall(r'\b\w+\b', text))

    def _to_markdown(self, text: str) -> str:
        """Normalize content to clean markdown."""
        if not text:
            return ""
        return text.strip()
