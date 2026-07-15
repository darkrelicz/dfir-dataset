import math
import re
from collections import Counter, defaultdict
from typing import Any

from evaluation.schemas import BenchmarkCase, CaseScore
from evaluation.structured_output import parse_json_object

TECHNIQUE_RE = re.compile(r"\b(?:T\d{4}(?:\.\d{3})?|AML\.[A-Za-z0-9_.-]+)\b")
IPV4_RE = re.compile(
    r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b"
)
URL_RE = re.compile(r"\bhttps?://[^\s<>'\")\]]+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
HASH_RE = re.compile(r"\b(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\b")
REGISTRY_RE = re.compile(r"\bHK(?:LM|CU|CR|U|CC)\\[^\s,;\"']+", re.IGNORECASE)
WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s,;\"']+")
UNIX_PATH_RE = re.compile(r"(?<!:)\/(?:[A-Za-z0-9._-]+\/)*[A-Za-z0-9._-]+")
DOMAIN_RE = re.compile(r"\b(?:[A-Z0-9-]+\.)+[A-Z]{2,}\b", re.IGNORECASE)
NEGATION_RE = re.compile(
    r"(?:\bno\b|\bnot\b|\bwithout\b|\bunsupported\b|"
    r"\bnot\s+supported\b|\bdid\s+not\b|\bdidn't\b)\s*$",
    re.IGNORECASE,
)

IOC_TYPE_ALIASES = {
    "ip": "ipv4",
    "ip_address": "ipv4",
    "ipv4_address": "ipv4",
    "email": "email_address",
    "email_address": "email_address",
    "sha256": "hash_sha256",
    "sha1": "hash_sha1",
    "md5": "hash_md5",
    "hash": "hash",
    "path": "file_path",
    "windows_path": "file_path",
    "linux_path": "file_path",
    "registry": "registry_key",
    "registry_path": "registry_key",
    "url_path": "url_path",
    "process": "process_name",
    "file": "file_name",
    "pipe": "named_pipe",
    "access_key_id": "cloud_access_key_id",
    "s3_uri": "cloud_storage_uri",
    "s3_bucket": "cloud_storage_bucket",
}

Indicator = tuple[str, str]


def score_case(
    case: BenchmarkCase,
    prediction: str,
    config: dict[str, Any],
) -> CaseScore:
    family = metric_family(case.scoring.metric)
    structured_config = config.get("structured_outputs", {})
    if (
        family in {"technique_f1", "ioc_f1", "ndcg"}
        and bool(structured_config.get("required", False))
    ):
        contract_error = structured_contract_error(family, prediction)
        if contract_error:
            return build_case_score(
                case,
                0.0,
                {
                    "scoring_mode": "invalid_structured_output",
                    "error": contract_error,
                },
                manual_review_recommended=True,
            )
    if family == "technique_f1":
        return score_technique_f1(case, prediction)
    if family == "ioc_f1":
        return score_iocs(case, prediction)
    if family == "ndcg":
        return score_ndcg(case, prediction, int(config.get("ndcg_k", 5)))
    return score_rubric(case, prediction)


def structured_contract_error(family: str, prediction: str) -> str | None:
    payload = parse_json_object(prediction)
    if payload is None:
        return "response did not contain a JSON object"
    keys_by_family = {
        "technique_f1": (
            "techniques",
            "mitre_techniques",
            "attack_techniques",
            "atlas_techniques",
        ),
        "ioc_f1": ("iocs",),
        "ndcg": ("ranked_actions", "ranking", "actions"),
    }
    keys = keys_by_family[family]
    present = [key for key in keys if key in payload]
    if not present:
        return f"response missing required array; expected one of {list(keys)}"
    if not any(isinstance(payload[key], list) for key in present):
        return f"structured field must be an array; received keys {present}"
    return None


def metric_family(metric: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", metric.casefold()).strip("_")
    if normalized in {"f1", "technique_f1", "attack_f1", "atlas_f1"}:
        return "technique_f1"
    if normalized in {"ioc_f1", "precision_recall", "precision_recall_f1"}:
        return "ioc_f1"
    if normalized.startswith("ndcg"):
        return "ndcg"
    if any(token in normalized for token in ("rubric", "accuracy", "quality")):
        return "rubric"
    raise ValueError(f"Unsupported evaluation metric: {metric}")


def score_technique_f1(case: BenchmarkCase, prediction: str) -> CaseScore:
    gold = collect_gold_labels(
        case.expected_answer.gold_labels,
        ("techniques", "mitre_techniques", "attack_techniques", "atlas_techniques"),
    )
    predicted = extract_techniques(prediction)
    precision, recall, f1 = precision_recall_f1(predicted, gold)
    return build_case_score(
        case,
        f1 * case.scoring.max_points,
        {
            "scoring_mode": "structured_or_text_techniques",
            "gold": sorted(gold),
            "predicted": sorted(predicted),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
    )


def extract_techniques(prediction: str) -> set[str]:
    structured = parse_json_object(prediction)
    if structured is not None:
        values: list[Any] = []
        for key in (
            "techniques",
            "mitre_techniques",
            "attack_techniques",
            "atlas_techniques",
        ):
            candidate = structured.get(key, [])
            if isinstance(candidate, str):
                candidate = [candidate]
            if isinstance(candidate, list):
                values.extend(candidate)
        if values:
            return {normalize_label(str(value)) for value in values if str(value).strip()}

    predicted = set()
    for match in TECHNIQUE_RE.finditer(prediction):
        if not technique_is_negated(prediction, match.start(), match.end()):
            predicted.add(normalize_label(match.group(0)))
    return predicted


def score_iocs(case: BenchmarkCase, prediction: str) -> CaseScore:
    gold = collect_gold_iocs(case.expected_answer.gold_labels.get("iocs", []))
    predicted, scoring_mode = extract_iocs(prediction)
    precision, recall, f1 = precision_recall_f1(predicted, gold)
    return build_case_score(
        case,
        f1 * case.scoring.max_points,
        {
            "scoring_mode": scoring_mode,
            "gold": serialize_indicators(gold),
            "predicted": serialize_indicators(predicted),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
    )


def score_ndcg(case: BenchmarkCase, prediction: str, k: int) -> CaseScore:
    gold_actions = case.expected_answer.gold_labels.get("ranked_actions", [])
    gold = normalize_ranked_items(gold_actions)
    predicted, scoring_mode = predicted_ranking(prediction, gold)
    ndcg = ndcg_at_k(predicted, gold, k)
    return build_case_score(
        case,
        ndcg * case.scoring.max_points,
        {
            "scoring_mode": scoring_mode,
            "gold": gold,
            "predicted": predicted[:k],
            "ndcg": ndcg,
            "k": k,
        },
    )


def score_rubric(case: BenchmarkCase, prediction: str) -> CaseScore:
    if case.expected_answer.required_concepts or case.expected_answer.forbidden_concepts:
        details = score_concept_aliases(case, prediction)
    else:
        details = score_legacy_substrings(case, prediction)

    include_score = details["include_score"]
    exclusion_score = details["exclusion_score"]
    normalized = (include_score * 0.8) + (exclusion_score * 0.2)
    return build_case_score(
        case,
        normalized * case.scoring.max_points,
        details,
        manual_review_recommended=True,
    )


def score_concept_aliases(case: BenchmarkCase, prediction: str) -> dict[str, Any]:
    required = case.expected_answer.required_concepts
    forbidden = case.expected_answer.forbidden_concepts
    required_hits = []
    required_misses = []
    forbidden_violations = []

    for concept in required:
        matched_alias = first_matching_alias(prediction, concept.aliases)
        row = concept_result(concept.id, concept.aliases, matched_alias)
        (required_hits if matched_alias else required_misses).append(row)

    for concept in forbidden:
        matched_alias = first_matching_alias(prediction, concept.aliases)
        if matched_alias:
            forbidden_violations.append(
                concept_result(concept.id, concept.aliases, matched_alias)
            )

    include_score = len(required_hits) / len(required) if required else 1.0
    exclusion_score = (
        1.0 - (len(forbidden_violations) / len(forbidden)) if forbidden else 1.0
    )
    return {
        "scoring_mode": "negation_aware_concept_aliases",
        "required_concepts_hit": required_hits,
        "required_concepts_missed": required_misses,
        "forbidden_concepts_violated": forbidden_violations,
        "include_score": include_score,
        "exclusion_score": exclusion_score,
        "legacy_must_include": case.expected_answer.must_include,
        "legacy_must_not_include": case.expected_answer.must_not_include,
    }


def score_legacy_substrings(case: BenchmarkCase, prediction: str) -> dict[str, Any]:
    must_include = case.expected_answer.must_include
    must_not_include = case.expected_answer.must_not_include
    include_hits = [item for item in must_include if text_contains(prediction, item)]
    include_misses = [item for item in must_include if item not in include_hits]
    exclusion_hits = [
        item for item in must_not_include if text_contains(prediction, item)
    ]
    include_score = len(include_hits) / len(must_include) if must_include else 1.0
    exclusion_score = (
        1.0 - (len(exclusion_hits) / len(must_not_include))
        if must_not_include
        else 1.0
    )
    return {
        "scoring_mode": "negation_aware_legacy_substrings",
        "must_include_hits": include_hits,
        "must_include_misses": include_misses,
        "must_not_include_violations": exclusion_hits,
        "include_score": include_score,
        "exclusion_score": exclusion_score,
    }


def first_matching_alias(prediction: str, aliases: list[str]) -> str | None:
    for alias in aliases:
        if text_contains(prediction, alias):
            return alias
    return None


def concept_result(
    concept_id: str,
    aliases: list[str],
    matched_alias: str | None,
) -> dict[str, Any]:
    return {"id": concept_id, "matched_alias": matched_alias, "aliases": aliases}


def build_case_score(
    case: BenchmarkCase,
    score: float,
    details: dict[str, Any],
    *,
    evaluator: str = "statistical",
    metric: str | None = None,
    manual_review_recommended: bool = False,
) -> CaseScore:
    max_points = float(case.scoring.max_points or 5.0)
    bounded_score = max(0.0, min(float(score), max_points))
    return CaseScore(
        case_id=case.case_id,
        task_type=case.task_type,
        evaluator=evaluator,
        metric=metric or case.scoring.metric,
        score=round(bounded_score, 4),
        normalized_score=round(bounded_score / max_points if max_points else 0.0, 4),
        max_points=max_points,
        details=details,
        manual_review_recommended=manual_review_recommended,
    )


def precision_recall_f1(
    predicted: set[Any],
    gold: set[Any],
) -> tuple[float, float, float]:
    if not predicted and not gold:
        return 1.0, 1.0, 1.0
    if not predicted or not gold:
        return 0.0, 0.0, 0.0
    true_positive = len(predicted & gold)
    precision = true_positive / len(predicted)
    recall = true_positive / len(gold)
    if precision + recall == 0:
        return precision, recall, 0.0
    return precision, recall, (2 * precision * recall) / (precision + recall)


def collect_gold_labels(gold_labels: dict[str, Any], keys: tuple[str, ...]) -> set[str]:
    labels: set[str] = set()
    for key in keys:
        values = gold_labels.get(key, [])
        if isinstance(values, str):
            values = [values]
        for value in values or []:
            labels.add(normalize_label(str(value)))
    return {label for label in labels if label}


def collect_gold_iocs(iocs: Any) -> set[Indicator]:
    return parse_indicator_rows(iocs)


def extract_iocs(text: str) -> tuple[set[Indicator], str]:
    structured = parse_json_object(text)
    if structured is not None and "iocs" in structured:
        return parse_indicator_rows(structured.get("iocs")), "structured_typed_iocs"

    values: set[Indicator] = set()
    typed_regexes = (
        ("url", URL_RE),
        ("email_address", EMAIL_RE),
        ("hash", HASH_RE),
        ("registry_key", REGISTRY_RE),
        ("file_path", WINDOWS_PATH_RE),
        ("file_path", UNIX_PATH_RE),
        ("ipv4", IPV4_RE),
        ("domain", DOMAIN_RE),
    )
    for indicator_type, regex in typed_regexes:
        for match in regex.finditer(text):
            if not is_negated_at(text, match.start()):
                values.add(normalize_indicator(indicator_type, match.group(0)))
    return {value for value in values if value[1]}, "legacy_regex_iocs"


def parse_indicator_rows(rows: Any) -> set[Indicator]:
    if isinstance(rows, (str, dict)):
        rows = [rows]
    values: set[Indicator] = set()
    for item in rows or []:
        if isinstance(item, dict):
            value = item.get("value") or item.get("indicator")
            indicator_type = item.get("type") or infer_ioc_type(str(value or ""))
        else:
            value = item
            indicator_type = infer_ioc_type(str(value or ""))
        if value:
            values.add(normalize_indicator(str(indicator_type), str(value)))
    return values


def normalize_indicator(indicator_type: str, value: str) -> Indicator:
    normalized_type = normalize_ioc_type(indicator_type, value)
    normalized_value = refang(value.strip().strip(".,;:()<>\"'"))
    case_sensitive = {"cloud_access_key_id", "mutex", "named_pipe"}
    if normalized_type not in case_sensitive:
        normalized_value = normalized_value.casefold()
    return normalized_type, normalized_value


def normalize_ioc_type(indicator_type: str, value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", indicator_type.casefold()).strip("_")
    normalized = IOC_TYPE_ALIASES.get(normalized, normalized)
    if normalized == "hash":
        return infer_hash_type(value)
    return normalized or infer_ioc_type(value)


def infer_ioc_type(value: str) -> str:
    stripped = value.strip()
    if IPV4_RE.fullmatch(stripped):
        return "ipv4"
    if "@" in stripped:
        return "email_address"
    if stripped.casefold().startswith(("http://", "https://", "hxxp://", "hxxps://")):
        return "url"
    if stripped.casefold().startswith("s3://"):
        return "cloud_storage_uri"
    if HASH_RE.fullmatch(stripped):
        return infer_hash_type(stripped)
    if re.match(r"^HK(?:LM|CU|CR|U|CC)\\", stripped, re.IGNORECASE):
        return "registry_key"
    if re.match(r"^[A-Za-z]:\\", stripped) or stripped.startswith("/"):
        return "file_path"
    return "unknown"


def infer_hash_type(value: str) -> str:
    lengths = {32: "hash_md5", 40: "hash_sha1", 64: "hash_sha256"}
    return lengths.get(len(value.strip()), "hash")


def refang(value: str) -> str:
    result = re.sub(r"^hxxps://", "https://", value, flags=re.IGNORECASE)
    result = re.sub(r"^hxxp://", "http://", result, flags=re.IGNORECASE)
    return re.sub(r"\[(?:\.|dot)\]|\(\.\)|\{\.\}", ".", result, flags=re.IGNORECASE)


def serialize_indicators(values: set[Indicator]) -> list[dict[str, str]]:
    return [
        {"type": indicator_type, "value": value}
        for indicator_type, value in sorted(values)
    ]


def normalize_label(value: str) -> str:
    return value.strip().upper().rstrip(".,;:")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def text_contains(text: str, needle: str) -> bool:
    if not needle:
        return False
    normalized_text = normalize_text(text)
    normalized_needle = normalize_text(needle)
    start = 0
    while True:
        index = normalized_text.find(normalized_needle, start)
        if index < 0:
            return False
        if not is_negated_at(normalized_text, index):
            return True
        start = index + len(normalized_needle)


def is_negated_at(text: str, index: int) -> bool:
    prefix = text[max(0, index - 32) : index]
    prefix = re.split(r"[.;!?\n]", prefix)[-1]
    return bool(NEGATION_RE.search(prefix))


def technique_is_negated(text: str, start: int, end: int) -> bool:
    if is_negated_at(text, start):
        return True
    suffix = text[end : end + 40]
    return bool(
        re.match(
            r"\s+(?:is\s+)?(?:not\s+supported|unsupported|not\s+evidenced|ruled\s+out)\b",
            suffix,
            re.IGNORECASE,
        )
    )


def normalize_ranked_items(items: Any) -> list[str]:
    ranked: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            value = item.get("id") or item.get("action") or item.get("label")
        else:
            value = item
        if value:
            ranked.append(str(value).strip())
    return ranked


def predicted_ranking(prediction: str, gold: list[str]) -> tuple[list[str], str]:
    structured = parse_json_object(prediction)
    if structured is not None:
        for key in ("ranked_actions", "ranking", "actions"):
            if key in structured and isinstance(structured[key], list):
                values = normalize_ranked_items(structured[key])
                return deduplicate(values), "structured_ranking"
    return predicted_ranking_from_text(prediction, gold), "legacy_text_position"


def deduplicate(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def predicted_ranking_from_text(prediction: str, gold: list[str]) -> list[str]:
    positions: list[tuple[int, str]] = []
    normalized_prediction = normalize_text(prediction)
    for item in gold:
        index = normalized_prediction.find(normalize_text(item))
        if index >= 0:
            positions.append((index, item))
    return [item for _, item in sorted(positions)]


def ndcg_at_k(predicted: list[str], gold: list[str], k: int) -> float:
    if not gold:
        return 1.0
    gold_lookup = {item.casefold(): item for item in gold}
    relevance = {item: len(gold) - index for index, item in enumerate(gold)}
    dcg = 0.0
    for index, predicted_item in enumerate(predicted[:k], 1):
        gold_item = gold_lookup.get(predicted_item.casefold())
        gain = relevance.get(gold_item or "", 0)
        dcg += gain / math.log2(index + 1)
    ideal = sum(
        relevance[item] / math.log2(index + 1)
        for index, item in enumerate(gold[:k], 1)
    )
    return dcg / ideal if ideal else 0.0


def aggregate_scores(
    scores: list[CaseScore],
    *,
    benchmark_fingerprint: str | None = None,
) -> dict[str, Any]:
    if not scores:
        return {
            "evaluator": None,
            "overall_normalized_score": 0.0,
            "task_scores": {},
            "case_ids": [],
        }
    evaluators = {score.evaluator for score in scores}
    if len(evaluators) != 1:
        raise ValueError("A scorecard cannot combine multiple evaluators")
    by_task: dict[str, list[CaseScore]] = defaultdict(list)
    for score in scores:
        by_task[score.task_type].append(score)

    task_scores = {}
    for task_type, task_cases in sorted(by_task.items()):
        normalized = [case.normalized_score for case in task_cases]
        task_scores[task_type] = {
            "cases": len(task_cases),
            "mean_normalized_score": round(sum(normalized) / len(normalized), 4),
            "manual_review_recommended": sum(
                1 for case in task_cases if case.manual_review_recommended
            ),
        }

    overall = sum(score.normalized_score for score in scores) / len(scores)
    result = {
        "evaluator": next(iter(evaluators)),
        "overall_normalized_score": round(overall, 4),
        "task_scores": task_scores,
        "metric_counts": dict(Counter(score.metric for score in scores)),
        "case_ids": sorted(score.case_id for score in scores),
    }
    if benchmark_fingerprint:
        result["benchmark_fingerprint"] = benchmark_fingerprint
    return result
