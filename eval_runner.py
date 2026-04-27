import argparse
import json
from pathlib import Path

from evaluator import evaluate_output
from main import generate_verdict_for_reviews
from schema import MomsVerdict


TEST_CASES = [
    {
        "name": "balanced_reviews",
        "reviews": [
            {"id": "r1", "text": "Very comfortable stroller"},
            {"id": "r2", "text": "Smooth ride and good quality"},
        ],
        "expected": {
            "confidence_min": 0.7,
            "has_disagreements": False,
        },
    },
    {
        "name": "conflicting_reviews",
        "reviews": [
            {"id": "r1", "text": "Very durable"},
            {"id": "r2", "text": "Broke after two days"},
        ],
        "expected": {
            "confidence_max": 0.7,
            "has_disagreements": True,
        },
    },
    {
        "name": "safety_issue",
        "reviews": [
            {"id": "r1", "text": "Wheel fell off, unsafe"},
            {"id": "r2", "text": "Feels dangerous"},
        ],
        "expected": {
            "confidence_min": 0.5,
            "has_disagreements": False,
        },
    },
    {
        "name": "arabic_reviews",
        "reviews": [
            {"id": "r1", "text": "?????? ????? ????? ?????????"},
            {"id": "r2", "text": "???? ??????"},
        ],
        "expected": {
            "confidence_min": 0.5,
        },
    },
    {
        "name": "mixed_language",
        "reviews": [
            {"id": "r1", "text": "Lightweight stroller"},
            {"id": "r2", "text": "?????? ?????"},
        ],
        "expected": {
            "has_disagreements": True,
        },
    },
    {
        "name": "sparse_data",
        "reviews": [
            {"id": "r1", "text": "Okay"},
        ],
        "expected": {
            "confidence_max": 0.6,
            "insufficient_flag": True,
        },
    },
    {
        "name": "empty_input",
        "reviews": [],
        "expected": {
            "should_fail": True,
        },
    },
    {
        "name": "generic_reviews",
        "reviews": [
            {"id": "r1", "text": "Nice"},
            {"id": "r2", "text": "Good"},
        ],
        "expected": {
            "confidence_max": 0.6,
            "insufficient_flag": True,
        },
    },
    {
        "name": "hallucination_trap",
        "reviews": [
            {"id": "r1", "text": "Good stroller"},
            {"id": "r2", "text": "Easy to use"},
        ],
        "expected": {
            "confidence_max": 0.6,
        },
    },
    {
        "name": "evidence_integrity",
        "reviews": [
            {"id": "r1", "text": "Very durable"},
            {"id": "r2", "text": "High quality"},
        ],
        "expected": {
            "confidence_min": 0.5,
        },
    },
    {
        "name": "high_conflict_multi_reviews",
        "reviews": [
            {"id": "r1", "text": "Excellent quality"},
            {"id": "r2", "text": "Terrible quality"},
            {"id": "r3", "text": "Not bad"},
            {"id": "r4", "text": "Very poor durability"},
        ],
        "expected": {
            "confidence_max": 0.6,
            "has_disagreements": True,
        },
    },
]


def run_case(case):
    return generate_verdict_for_reviews(case["reviews"])


def load_cached_case(cache_dir: Path, case_name: str):
    cache_path = cache_dir / f"{case_name}.json"
    if not cache_path.exists():
        return None
    return MomsVerdict.model_validate(
        json.loads(cache_path.read_text(encoding="utf-8"))
    )


def check_expectations(verdict, expected):
    checks = []

    if "confidence_min" in expected:
        checks.append(verdict.confidence_score >= expected["confidence_min"])

    if "confidence_max" in expected:
        checks.append(verdict.confidence_score <= expected["confidence_max"])

    if "has_disagreements" in expected:
        checks.append((len(verdict.disagreements) > 0) == expected["has_disagreements"])

    if "insufficient_flag" in expected:
        checks.append(
            ("limited_review_count" in verdict.insufficient_data_flags)
            == expected["insufficient_flag"]
        )

    return all(checks) if checks else True


def check_evidence_integrity(verdict, reviews):
    review_ids = {r["id"] for r in reviews}

    for section in verdict.pros + verdict.cons:
        for ev in section.evidence:
            if ev.review_id not in review_ids:
                return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Call the model for each test case instead of loading cached outputs.",
    )
    parser.add_argument(
        "--cache-dir",
        default="eval_cache",
        help="Directory for cached outputs when --generate is used.",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(exist_ok=True, parents=True)

    results = []
    for case in TEST_CASES:
        verdict = None
        case_error = None

        if args.generate:
            try:
                verdict = run_case(case)
                (cache_dir / f"{case['name']}.json").write_text(
                    json.dumps(verdict.model_dump(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as exc:
                case_error = str(exc)
                cached_verdict = load_cached_case(cache_dir, case["name"])
                if cached_verdict is not None:
                    verdict = cached_verdict
                    case_error = f"{case_error} (loaded cached verdict)"
        else:
            cache_path = cache_dir / f"{case['name']}.json"
            if cache_path.exists():
                verdict = MomsVerdict.model_validate(
                    json.loads(cache_path.read_text(encoding="utf-8"))
                )

        score = evaluate_output(verdict, case["reviews"])

        expectation_pass = True
        if "expected" in case:
            if verdict is None:
                expectation_pass = bool(case["expected"].get("should_fail"))
            else:
                expectation_pass = check_expectations(verdict, case["expected"])

        grounding_valid = False if verdict is None else check_evidence_integrity(verdict, case["reviews"])

        result_row = {
            "case": case["name"],
            "expectation_pass": expectation_pass,
            "grounding_valid": grounding_valid,
            **score,
        }
        if case_error:
            result_row["error"] = case_error

        results.append(result_row)

    print(json.dumps(results, ensure_ascii=False, indent=2))

    passed = sum(1 for r in results if r["expectation_pass"])
    total = len(results)
    print(f"\nExpectation Score: {passed}/{total}")


if __name__ == "__main__":
    main()
