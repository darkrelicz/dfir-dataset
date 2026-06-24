from dataclasses import dataclass, field
from typing import Protocol

from synthesizers.schemas import PromptRecord


@dataclass(frozen=True)
class ModelResponse:
    model: str
    text: str 
    metadata: dict = field(default_factory=dict)


class ModelClient(Protocol):
    def generate(self, prompt_record: PromptRecord) -> ModelResponse:
        """Generate raw text for one prompt record."""
        ...
