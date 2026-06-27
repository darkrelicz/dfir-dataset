import os
from typing import Any

from google import genai
from pydantic import TypeAdapter

from synthesizers.clients.base import ModelResponse
from synthesizers.schemas import InstructionPair, PromptRecord


INSTRUCTION_PAIR_LIST_SCHEMA = TypeAdapter(list[InstructionPair]).json_schema()
INSTRUCTION_PAIR_RESPONSE_FORMAT = {
    "type": "text",
    "mime_type": "application/json",
    "schema": INSTRUCTION_PAIR_LIST_SCHEMA,
}
INTERACTION_METADATA_FIELDS = ("id", "model", "status", "usage")


class GeminiClient:
    """Thin Google GenAI SDK wrapper for one-prompt-at-a-time generation."""

    def __init__(self, model_config: dict[str, Any], generation_config: dict[str, Any]):
        api = str(model_config.get("api", "interactions"))
        if api != "interactions":
            raise ValueError(f"Unsupported Gemini API mode: {api}")

        self.model = str(model_config["primary"])
        self.api_key_env = str(model_config.get("api_key_env", "GEMINI_API_KEY"))
        self.temperature = generation_config.get("temperature")
        self.thinking_level = generation_config.get("thinking_level")

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing {self.api_key_env}. Add it to .env or export it first.")
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt_record: PromptRecord) -> ModelResponse:
        interaction = self.client.interactions.create(
            model=self.model,
            input=prompt_record.prompt,
            generation_config=self._generation_config(),
            response_format=INSTRUCTION_PAIR_RESPONSE_FORMAT,
        )
        return ModelResponse(
            model=self.model,
            text=self._output_text(interaction),
            metadata=self._metadata_from_interaction(interaction),
        )

    def _generation_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        if self.temperature is not None:
            config["temperature"] = float(self.temperature)
        if self.thinking_level:
            config["thinking_level"] = str(self.thinking_level)
        return config

    def _metadata_from_interaction(self, interaction) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for attr in INTERACTION_METADATA_FIELDS:
            if hasattr(interaction, attr):
                value = getattr(interaction, attr)
                metadata[attr] = self._metadata_value(value)
        return metadata

    def _output_text(self, interaction) -> str:
        output_text = getattr(interaction, "output_text", None)
        if output_text is None:
            raise RuntimeError("Gemini response did not include output_text")
        return str(output_text)

    def _metadata_value(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "to_json_dict"):
            return value.to_json_dict()
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, (dict, list)):
            return value
        return str(value)
