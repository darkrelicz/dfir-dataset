import json
import logging
import os
from pathlib import Path
from typing import Any, Protocol

import requests

from evaluation.schemas import BenchmarkCase

logger = logging.getLogger(__name__)
RESPONSE_PREVIEW_CHARS = 500
RESERVED_REQUEST_FIELDS = {"messages", "model"}


class EvaluationClient(Protocol):
    """Model client interface used by the Phase 6 evaluator."""

    def generate(self, case: BenchmarkCase, messages: list[dict[str, str]]) -> str:
        ...


class PredictionFileClient:
    """Replay predictions from JSONL keyed by case_id."""

    def __init__(self, path: Path) -> None:
        logger.info("Loading prediction file: path=%s", path)
        self.predictions = load_prediction_file(path)
        logger.info(
            "Loaded prediction file: path=%s predictions=%s",
            path,
            len(self.predictions),
        )

    def generate(self, case: BenchmarkCase, messages: list[dict[str, str]]) -> str:
        if case.case_id not in self.predictions:
            raise KeyError(f"Missing prediction for case_id={case.case_id}")
        return self.predictions[case.case_id]


class OpenAICompatibleClient:
    """Minimal chat-completions client for llama-server, vLLM, or LM Studio."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.base_url = str(
            config.get("base_url", "http://127.0.0.1:8080/v1")
        ).rstrip("/")
        self.model = str(config.get("model", "GLM-4.7-Flash"))
        self.temperature = float(config.get("temperature", 0.0))
        self.top_p = float(config.get("top_p", 1.0))
        self.max_tokens = int(config.get("max_tokens", 1200))
        self.timeout = int(config.get("timeout_seconds", 180))
        self.response_format = normalize_response_format(config.get("response_format"))
        request_overrides = config.get("request_overrides", {})
        if not isinstance(request_overrides, dict):
            raise ValueError("request_overrides must be a mapping")
        reserved = RESERVED_REQUEST_FIELDS.intersection(request_overrides)
        if reserved:
            raise ValueError(
                "request_overrides cannot replace reserved fields: "
                + ", ".join(sorted(reserved))
            )
        self.request_overrides = dict(request_overrides)
        api_key_env = str(config.get("api_key_env", "OPENAI_API_KEY"))
        self.api_key = os.getenv(api_key_env, "")
        logger.info(
            "Configured OpenAI-compatible client: base_url=%s model=%s "
            "timeout_seconds=%s max_tokens=%s",
            self.base_url,
            self.model,
            self.timeout,
            self.max_tokens,
        )

    def generate(self, case: BenchmarkCase, messages: list[dict[str, str]]) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        if self.response_format is not None:
            payload["response_format"] = self.response_format
        payload.update(self.request_overrides)
        endpoint = f"{self.base_url}/chat/completions"
        logger.info(
            "Sending chat completion request: case_id=%s endpoint=%s",
            case.case_id,
            endpoint,
        )
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        logger.info(
            "Received chat completion response: case_id=%s status_code=%s",
            case.case_id,
            response.status_code,
        )
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        content = message_content_to_text(message.get("content")).strip()
        reasoning = message_content_to_text(
            message.get("reasoning_content") or message.get("reasoning")
        )
        finish_reason = choice.get("finish_reason")
        response_model = data.get("model")
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        logger.info(
            "Parsed chat completion response: case_id=%s requested_model=%s "
            "response_model=%s finish_reason=%s content_chars=%s "
            "reasoning_chars=%s completion_tokens=%s",
            case.case_id,
            self.model,
            response_model,
            finish_reason,
            len(content),
            len(reasoning),
            usage.get("completion_tokens"),
        )
        if response_model and str(response_model) != self.model:
            logger.warning(
                "Chat completion model mismatch: case_id=%s requested_model=%s "
                "response_model=%s",
                case.case_id,
                self.model,
                response_model,
            )
        if not content:
            logger.warning(
                "Chat completion returned empty content: case_id=%s "
                "finish_reason=%s reasoning_chars=%s message_fields=%s",
                case.case_id,
                finish_reason,
                len(reasoning),
                sorted(message),
            )
        else:
            logger.debug(
                "Chat completion content preview: case_id=%s content=%r",
                case.case_id,
                response_preview(content),
            )
        return content


def normalize_response_format(value: Any) -> dict[str, Any] | None:
    """Normalize a concise config value to the OpenAI request shape."""

    if value is None or value is False:
        return None
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"", "none", "disabled"}:
            return None
        return {"type": normalized}
    if isinstance(value, dict):
        return dict(value)
    raise ValueError("response_format must be a string or mapping")


def message_content_to_text(value: Any) -> str:
    """Extract text from string or OpenAI-style multipart message content."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return str(value)


def response_preview(value: str, limit: int = RESPONSE_PREVIEW_CHARS) -> str:
    """Return a bounded single-line response preview for diagnostic logs."""

    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def build_client(
    mode: str,
    config: dict[str, Any],
    predictions_path: Path | None,
) -> EvaluationClient:
    normalized = mode.strip().lower()
    if normalized == "prediction_file":
        if predictions_path is None:
            raise ValueError(
                "prediction_file mode requires --predictions or "
                "generation.predictions_path in the evaluation config"
            )
        return PredictionFileClient(predictions_path)
    if normalized == "openai_compatible":
        return OpenAICompatibleClient(config)
    raise ValueError(f"Unsupported evaluation generation mode: {mode}")


def load_prediction_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing prediction file: {path}")

    predictions: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            case_id = row.get("case_id")
            if not case_id:
                raise ValueError(f"Prediction row {line_number} missing case_id")
            case_id = str(case_id)
            if case_id in predictions:
                raise ValueError(
                    f"Prediction row {line_number} duplicates case_id={case_id}"
                )
            prediction = row.get("prediction")
            if prediction is None:
                raise ValueError(f"Prediction row {line_number} missing prediction")
            predictions[case_id] = str(prediction)
    return predictions
