from evaluation.judge import LocalLLMJudge, build_judge_messages
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


def test_judge_supplies_and_records_acceptable_variant() -> None:
    case = BenchmarkCase(
        case_id="case-ranking",
        task_type="triage_prioritization",
        difficulty="mid",
        prompt="Rank the actions.",
        expected_answer={
            "gold_labels": {"ranking": ["A1", "A2", "A3"]},
            "acceptable_variants": [["A2", "A1", "A3"]],
        },
        scoring={"metric": "ndcg@5", "max_points": 5},
    )
    messages = build_judge_messages(case, "A2, A1, A3")

    assert '"acceptable_variants": [' in messages[1]["content"]
    assert '"A2"' in messages[1]["content"]

    judge = LocalLLMJudge({"model": "judge-model", "validation_retries": 0})
    judge.client = StubClient(
        [
            '{"score": 5, "reason": "Matches an allowed ordering", '
            '"criteria": {}, "matched_acceptable_variant": 0}'
        ]
    )

    score = judge.score(case, "A2, A1, A3")

    assert score.score == 5
    assert score.details["matched_acceptable_variant"] == 0
    assert score.details["acceptable_variant_count"] == 1


def test_judge_rejects_out_of_range_acceptable_variant() -> None:
    case = BenchmarkCase(
        case_id="case-ranking",
        task_type="triage_prioritization",
        difficulty="mid",
        prompt="Rank the actions.",
        expected_answer={"acceptable_variants": [["A2", "A1"]]},
        scoring={"metric": "ndcg@5", "max_points": 5},
    )
    judge = LocalLLMJudge({"model": "judge-model", "validation_retries": 0})
    judge.client = StubClient(
        [
            '{"score": 5, "reason": "Claims a missing variant", '
            '"criteria": {}, "matched_acceptable_variant": 2}'
        ]
    )

    try:
        judge.score(case, "A2, A1")
    except ValueError as exc:
        assert "outside allowed range" in str(exc)
    else:
        raise AssertionError("Expected an invalid acceptable-variant index to fail")
