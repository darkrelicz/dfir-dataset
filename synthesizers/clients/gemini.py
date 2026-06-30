import json
import os
from typing import Any

from google import genai
from google.genai import types
from pydantic import TypeAdapter

from synthesizers.clients.base import ModelResponse
from synthesizers.schemas import InstructionPair, PromptRecord


UNSUPPORTED_RESPONSE_SCHEMA_KEYS = {"additionalProperties", "additional_properties"}
SUPPORTED_APIS = {"generate_content", "models.generate_content"}
GENERATE_CONTENT_METADATA_FIELDS = (
    "response_id",
    "model_version",
    "usage_metadata",
    "prompt_feedback",
    "model_status",
)


def sanitize_response_schema(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize_response_schema(item)
            for key, item in value.items()
            if key not in UNSUPPORTED_RESPONSE_SCHEMA_KEYS
        }
    if isinstance(value, list):
        return [sanitize_response_schema(item) for item in value]
    return value


INSTRUCTION_PAIR_LIST_ADAPTER = TypeAdapter(list[InstructionPair])
INSTRUCTION_PAIR_RESPONSE_SCHEMA = sanitize_response_schema(
    INSTRUCTION_PAIR_LIST_ADAPTER.json_schema()
)


class GeminiClient:
    """Thin Google GenAI SDK wrapper for one-prompt-at-a-time generation."""

    def __init__(self, model_config: dict[str, Any], generation_config: dict[str, Any]):
        api = str(model_config.get("api", "generate_content"))
        if api not in SUPPORTED_APIS:
            raise ValueError(f"Unsupported Gemini API mode: {api}")

        self.model = str(model_config["primary"])
        self.api_key_env = str(model_config.get("api_key_env", "GEMINI_API_KEY"))
        self.temperature = generation_config.get("temperature")
        self.thinking_budget = generation_config.get("thinking_budget")

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing {self.api_key_env}. Add it to .env or export it first.")
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt_record: PromptRecord) -> ModelResponse:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt_record.prompt,
            config=self._generation_config(),
        )
        return ModelResponse(
            model=self.model,
            text=self._output_text(response),
            metadata=self._metadata_from_response(response),
        )

    def _generation_config(self) -> types.GenerateContentConfig:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=INSTRUCTION_PAIR_RESPONSE_SCHEMA,
            thinking_config=self._thinking_config(),
        )
        if self.temperature is not None:
            config.temperature = float(self.temperature)
        return config

    def _thinking_config(self) -> types.ThinkingConfig | None:
        if self.thinking_budget is None:
            return None

        config = types.ThinkingConfig()
        config.thinking_budget = int(self.thinking_budget)
        return config

    def _metadata_from_response(self, response) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for attr in GENERATE_CONTENT_METADATA_FIELDS:
            if hasattr(response, attr):
                value = getattr(response, attr)
                metadata[attr] = self._metadata_value(value)
        return metadata

    def _output_text(self, response) -> str:
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            pairs = INSTRUCTION_PAIR_LIST_ADAPTER.validate_python(parsed)
            return json.dumps(
                INSTRUCTION_PAIR_LIST_ADAPTER.dump_python(pairs, mode="json"),
                ensure_ascii=False,
            )

        output_text = getattr(response, "text", None)
        if output_text is None:
            raise RuntimeError("Gemini response did not include text output")
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
