from evaluation.judge import LocalLLMJudge
from evaluation.schemas import BenchmarkCase


class StubClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.requests: list[list[dict[str, str]]] = []

    def generate(
        self,
        case: BenchmarkCase,
        messages: list[dict[str, str]],
    ) -> str:
        self.requests.append(messages)
        return next(self.responses)


def test_judge_retry_includes_invalid_assistant_response() -> None:
    case = BenchmarkCase(
        case_id="case-1",
        task_type="incident_report_generation",
        difficulty="mid",
        prompt="Evaluate this report.",
        scoring={"metric": "report_quality_1_5", "max_points": 5},
    )
    judge = LocalLLMJudge(
        {
            "model": "judge-model",
            "validation_retries": 1,
        }
    )
    client = StubClient(
        [
            "This is not JSON.",
            '{"score": 4, "reason": "Mostly complete", "criteria": {}}',
        ]
    )
    judge.client = client

    score = judge.score(case, "candidate report")

    assert score.score == 4
    assert score.details["validation_attempts"] == 2
    retry_messages = client.requests[1]
    assert retry_messages[-2] == {
        "role": "assistant",
        "content": "This is not JSON.",
    }
    assert "did not contain a JSON object" in retry_messages[-1]["content"]
