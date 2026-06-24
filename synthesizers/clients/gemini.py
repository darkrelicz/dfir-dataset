import os
from typing import Any

from pydantic import TypeAdapter

from synthesizers.clients.base import ModelResponse
from synthesizers.schemas import InstructionPair, PromptRecord


class GeminiClient:
    """Thin Google GenAI SDK wrapper for one-prompt-at-a-time generation."""

    def __init__(self, model_config: dict[str, Any], generation_config: dict[str, Any]):
        self.model = str(model_config["primary"])
        self.api_key_env = str(model_config.get("api_key_env", "GEMINI_API_KEY"))
        self.temperature = generation_config.get("temperature")
        self.thinking_level = model_config.get("thinking_level")
        self._client = None

    def generate(self, prompt_record: PromptRecord) -> ModelResponse:
        interaction = self._genai_client().interactions.create(
            model=self.model,
            input=prompt_record.prompt,
            generation_config=self._generation_config(),
            response_format=self._response_format(),
        )
        return ModelResponse(
            model=self.model,
            text=self._output_text(interaction),
            metadata=self._metadata_from_interaction(interaction),
        )

    def _genai_client(self):
        if self._client is not None:
            return self._client

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Missing {self.api_key_env}. Add it to .env or export it first."
            )

        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "Missing google-genai. Install project dependencies before generation."
            ) from exc

        self._client = genai.Client(api_key=api_key)
        return self._client

    def _generation_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        if self.temperature is not None:
            config["temperature"] = float(self.temperature)
        if self.thinking_level:
            config["thinking_level"] = str(self.thinking_level)
        return config

    def _response_format(self) -> dict[str, Any]:
        schema = TypeAdapter(list[InstructionPair]).json_schema()
        return {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        }

    def _metadata_from_interaction(self, interaction) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for attr in ("id", "finish_reason", "usage_metadata"):
            if hasattr(interaction, attr):
                value = getattr(interaction, attr)
                metadata[attr] = self._json_safe(value)
        return metadata

    def _output_text(self, interaction) -> str:
        output_text = getattr(interaction, "output_text", None)
        if output_text is None:
            raise RuntimeError("Gemini response did not include output_text")
        return str(output_text)

    def _json_safe(self, value):
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "to_json_dict"):
            return value.to_json_dict()
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        return str(value)
