import re
from typing import Dict, List

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")

def _confidence_band_expected(reviews: List[dict]) -> str:
    if len(reviews) == 0:
        return "refusal"
    if len(reviews) <= 2:
        return "low"
    if len(reviews) <= 4:
        return "medium"
    return "high"


def evaluate_output(verdict, reviews) -> Dict[str, int]:
    score = {
        "structure": 0,
        "grounding": 0,
        "uncertainty": 0,
        "multilingual": 0,
    }

    if verdict is None:
        return score

    score["structure"] = 1

    all_ids = {r["id"] for r in reviews if isinstance(r, dict) and "id" in r}
    grounded = True

    for point in verdict.pros + verdict.cons:
        if not point.evidence:
            grounded = False
            continue
        for ev in point.evidence:
            if ev.review_id not in all_ids:
                grounded = False
            if not isinstance(ev.review_id, str) or not ev.review_id.strip():
                grounded = False

    score["grounding"] = int(grounded)

    expected_band = _confidence_band_expected(reviews)
    confidence = verdict.confidence_score

    if expected_band == "refusal":
        score["uncertainty"] = int(
            confidence == 0 and verdict.user_warning is not None and not verdict.pros and not verdict.cons
        )
    elif expected_band == "low":
        score["uncertainty"] = int(confidence <= 0.6)
    elif expected_band == "medium":
        score["uncertainty"] = int(0.35 <= confidence <= 0.85)
    else:
        score["uncertainty"] = int(confidence >= 0.5)

    score["multilingual"] = int(
        bool(ARABIC_RE.search(verdict.summary_ar)) and bool(re.search(r"[A-Za-z]", verdict.summary_en))
    )

    return score
