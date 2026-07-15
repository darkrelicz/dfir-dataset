import logging

from evaluation.model_clients import OpenAICompatibleClient
from evaluation.schemas import BenchmarkCase


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def benchmark_case() -> BenchmarkCase:
    return BenchmarkCase(
        case_id="case-1",
        task_type="incident_report_generation",
        difficulty="mid",
        prompt="Evaluate this report.",
    )


def test_client_sends_structured_output_and_request_overrides(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(*args, **kwargs) -> FakeResponse:
        captured.update(kwargs["json"])
        return FakeResponse(
            {
                "model": "judge-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": '{"score": 4, "reason": "good"}',
                                }
                            ]
                        },
                    }
                ],
                "usage": {"completion_tokens": 12},
            }
        )

    monkeypatch.setattr("evaluation.model_clients.requests.post", fake_post)
    client = OpenAICompatibleClient(
        {
            "model": "judge-model",
            "response_format": "json_object",
            "request_overrides": {
                "chat_template_kwargs": {"enable_thinking": False}
            },
        }
    )

    result = client.generate(
        benchmark_case(),
        [{"role": "user", "content": "score"}],
    )

    assert result == '{"score": 4, "reason": "good"}'
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["chat_template_kwargs"] == {"enable_thinking": False}


def test_client_reports_reasoning_only_completion(monkeypatch, caplog) -> None:
    def fake_post(*args, **kwargs) -> FakeResponse:
        return FakeResponse(
            {
                "model": "canonical-model-name",
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": "",
                            "reasoning_content": "thinking without a final answer",
                        },
                    }
                ],
            }
        )

    monkeypatch.setattr("evaluation.model_clients.requests.post", fake_post)
    client = OpenAICompatibleClient({"model": "judge-alias"})

    with caplog.at_level(logging.INFO):
        result = client.generate(
            benchmark_case(),
            [{"role": "user", "content": "score"}],
        )

    assert result == ""
    assert "finish_reason=length" in caplog.text
    assert "reasoning_chars=31" in caplog.text
    assert "requested_model=judge-alias" in caplog.text
    assert "response_model=canonical-model-name" in caplog.text
