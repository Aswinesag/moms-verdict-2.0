import json
import os
import re
from pathlib import Path

import requests

from prompt import SYSTEM_PROMPT, build_prompt
from schema import MomsVerdict

MODEL = "meta-llama/llama-3.1-70b-instruct"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_REVIEWS_PATH = Path("data/reviews.json")
DOTENV_PATH = Path(".env")

THEME_KEYWORDS = {
    "quality": ["quality", "well made", "well-made", "durable", "build quality", "????", "???", "?????", "?????"],
    "sturdy": ["sturdy", "solid", "stable", "????"],
    "smooth to push": ["smooth", "push", "???", "??? ?????"],
    "easy to use": [
        "easy to use",
        "easy",
        "simple",
        "????? ?????????",
        "???? ?????????",
        "??? ?????????",
    ],
    "durability": [
        "durable",
        "durability",
        "well made",
        "well-made",
        "broken",
        "broke",
        "break",
        "broke after",
        "???? ??????",
        "???? ?????",
        "?????",
        "??????",
    ],
    "heavy": ["heavy", "heavier", "weight", "heavyweight", "????"],
    "weight": ["heavy", "heavier", "weight", "heavyweight", "????", "????"],
    "safety": ["safe", "safety", "unstable", "not safe", "broke", "broken", "unsafe", "dangerous", "??? ???"],
    "price": ["price", "priced", "overpriced", "expensive", "value", "cost", "???", "????"],
}

GENERIC_REVIEW_SET = {
    "nice",
    "good",
    "okay",
    "good product",
    "good stroller",
    "works fine",
    "fine",
    "decent",
}

POSITIVE_SIGNAL_WORDS = {
    "good",
    "great",
    "excellent",
    "durable",
    "sturdy",
    "comfortable",
    "smooth",
    "easy",
    "quality",
    "reliable",
    "lightweight",
    "?????",
    "???",
    "?????",
    "????",
    "????",
}

NEGATIVE_SIGNAL_WORDS = {
    "bad",
    "poor",
    "broken",
    "broke",
    "unsafe",
    "dangerous",
    "heavy",
    "expensive",
    "overpriced",
    "weak",
    "unstable",
    "????",
    "???",
    "???",
    "??? ???",
}


def _contains_term(text: str, term: str) -> bool:
    if not term:
        return False
    lowered = text.lower()
    normalized = term.lower().strip()
    if normalized.isascii() and " " not in normalized:
        pattern = r"(?<!\w)" + re.escape(normalized) + r"(?!\w)"
        return re.search(pattern, lowered) is not None
    return normalized in lowered


def _parse_dotenv_value(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value.strip()


def load_dotenv_file(path: Path = DOTENV_PATH) -> dict:
    if not path.exists():
        return {}

    loaded = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue
        loaded[key] = _parse_dotenv_value(value)

    return loaded


def load_api_key() -> str:
    dotenv_values = load_dotenv_file()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip() or dotenv_values.get(
        "OPENROUTER_API_KEY", ""
    ).strip()
    if not api_key:
        raise RuntimeError(
            "Missing OPENROUTER_API_KEY environment variable. "
            "Set it in your shell or add OPENROUTER_API_KEY=... to .env."
        )
    return api_key


def call_llm(prompt: str) -> str:
    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {load_api_key()}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    response.raise_for_status()

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("OpenRouter returned non-JSON response") from exc

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected OpenRouter response shape: {result}") from exc


def extract_json(text: str) -> str:
    decoder = json.JSONDecoder()
    start = text.find("{")

    while start != -1:
        try:
            obj, _ = decoder.raw_decode(text[start:])
            return json.dumps(obj, ensure_ascii=False)
        except json.JSONDecodeError:
            start = text.find("{", start + 1)

    raise ValueError("No JSON object found in model output")


def load_reviews(path: Path = DEFAULT_REVIEWS_PATH):
    with path.open(encoding="utf-8") as f:
        reviews = json.load(f)

    if not isinstance(reviews, list) or not reviews:
        raise ValueError("reviews.json must contain a non-empty list of review objects")

    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("Each review must be an object")
        if "id" not in review or "text" not in review:
            raise ValueError("Each review must have 'id' and 'text' fields")

    return reviews


def validate_against_reviews(verdict: MomsVerdict, reviews):
    review_ids = {review["id"] for review in reviews}
    invalid_ids = set()

    for point in verdict.pros + verdict.cons:
        for evidence in point.evidence:
            if evidence.review_id not in review_ids:
                invalid_ids.add(evidence.review_id)

    if invalid_ids:
        raise ValueError(f"Invalid evidence review_id(s): {sorted(invalid_ids)}")


def _theme_for_label(label: str):
    normalized = label.lower().strip()
    if "easy to use" in normalized:
        return "easy to use"
    if "quality" in normalized:
        return "quality"
    if "durable" in normalized or "durability" in normalized or "broke" in normalized or "broken" in normalized:
        return "durability"
    if "sturdy" in normalized or "solid" in normalized or "stable" in normalized:
        return "sturdy"
    if "smooth" in normalized and "push" in normalized:
        return "smooth to push"
    if "heavy" in normalized or "weight" in normalized or "light" in normalized:
        return "weight"
    if "safe" in normalized or "safety" in normalized or "unstable" in normalized:
        return "safety"
    if "price" in normalized or "value" in normalized or "cost" in normalized or "expensive" in normalized:
        return "price"
    return None


def _review_text(review):
    return str(review.get("text", "")).strip().lower()


def _is_generic_review(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    words = [word for word in normalized.split(" ") if word]
    if not normalized:
        return True
    if normalized in GENERIC_REVIEW_SET:
        return True
    if len(words) <= 2:
        return True
    if len(words) <= 3 and not any(word in normalized for word in POSITIVE_SIGNAL_WORDS | NEGATIVE_SIGNAL_WORDS):
        return True
    return False


def _review_sentiment(text: str) -> int:
    lowered = text.lower()
    positive = sum(1 for word in POSITIVE_SIGNAL_WORDS if _contains_term(lowered, word))
    negative = sum(1 for word in NEGATIVE_SIGNAL_WORDS if _contains_term(lowered, word))
    if positive > negative:
        return 1
    if negative > positive:
        return -1
    return 0


def _evidence_texts(point, reviews):
    by_id = {review["id"]: review["text"] for review in reviews}
    texts = []
    for evidence in point.evidence:
        base = by_id.get(evidence.review_id, "")
        snippet = evidence.snippet or ""
        texts.append(f"{base} {snippet}".strip().lower())
    return texts


def _theme_support_from_text(text: str, theme: str) -> int:
    lowered = text.lower()
    keywords = THEME_KEYWORDS.get(theme, [])
    if not any(_contains_term(lowered, keyword) for keyword in keywords):
        return 0

    positive = sum(1 for word in POSITIVE_SIGNAL_WORDS if _contains_term(lowered, word))
    negative = sum(1 for word in NEGATIVE_SIGNAL_WORDS if _contains_term(lowered, word))
    if positive > negative:
        return 1
    if negative > positive:
        return -1
    return 0


def validate_semantics(verdict: MomsVerdict, reviews):
    issues = []
    review_text_by_id = {review["id"]: review["text"].lower() for review in reviews}
    pros_themes = {}
    cons_themes = {}
    theme_polarities = {}

    for point in verdict.pros + verdict.cons:
        theme = _theme_for_label(point.point)
        if not theme:
            continue

        keywords = THEME_KEYWORDS.get(theme, [])
        joined = " ".join(_evidence_texts(point, reviews))

        if theme == "quality" and (
            _contains_term(joined, "easy to use")
            or _contains_term(joined, "سهولة الاستخدام")
            or _contains_term(joined, "سهلة الاستخدام")
        ):
            issues.append(f"point '{point.point}' mixes quality with usability")
        elif theme == "easy to use" and _contains_term(joined, "quality") and not (
            _contains_term(joined, "easy to use")
            or _contains_term(joined, "سهولة الاستخدام")
            or _contains_term(joined, "سهلة الاستخدام")
        ):
            issues.append(f"point '{point.point}' uses quality evidence for usability")
        elif keywords and not any(_contains_term(joined, keyword) for keyword in keywords):
            issues.append(f"point '{point.point}' is not directly supported by its evidence")

    for review in reviews:
        text = str(review.get("text", "")).lower()
        for theme in THEME_KEYWORDS:
            polarity = _theme_support_from_text(text, theme)
            if polarity == 0:
                continue
            bucket = theme_polarities.setdefault(theme, {"pos": False, "neg": False})
            if polarity > 0:
                bucket["pos"] = True
            else:
                bucket["neg"] = True

    for point in verdict.pros:
        theme = _theme_for_label(point.point)
        if theme:
            pros_themes[theme] = pros_themes.get(theme, 0) + 1
    for point in verdict.cons:
        theme = _theme_for_label(point.point)
        if theme:
            cons_themes[theme] = cons_themes.get(theme, 0) + 1

    theme_mix = {theme for theme in pros_themes if theme in cons_themes}

    disagreement_themes = {str(theme).lower().strip() for theme in verdict.disagreements}
    for theme in disagreement_themes:
        polarity = theme_polarities.get(theme, {})
        review_mixed = polarity.get("pos") and polarity.get("neg")
        if theme not in theme_mix and not review_mixed:
            issues.append(f"disagreement theme '{theme}' is not mixed across pros and cons")

    weight_mixed = ("weight" in theme_mix) or (
        theme_polarities.get("weight", {}).get("pos")
        and theme_polarities.get("weight", {}).get("neg")
    )
    if weight_mixed and "weight" not in disagreement_themes:
        issues.append("missing weight in disagreements")
        if "weight" in " ".join(review_text_by_id.values()) and verdict.summary_en and "weight" not in verdict.summary_en.lower() and "heavy" not in verdict.summary_en.lower():
            issues.append("summary_en omits the mixed weight theme")

    return issues


def calibrate_uncertainty(verdict: MomsVerdict, reviews):
    texts = [_review_text(review) for review in reviews if isinstance(review, dict)]
    review_count = len(texts)
    generic_count = sum(_is_generic_review(text) for text in texts)
    sentiments = [_review_sentiment(text) for text in texts]
    has_positive = any(sent > 0 for sent in sentiments)
    has_negative = any(sent < 0 for sent in sentiments)
    has_mixed_reviews = has_positive and has_negative
    flags = set(verdict.insufficient_data_flags)

    cap = 0.95
    if review_count <= 1:
        cap = 0.45
        flags.add("limited_review_count")
    elif review_count <= 2:
        if generic_count >= 1:
            cap = 0.6
            flags.add("limited_review_count")
        elif has_mixed_reviews:
            cap = 0.7
        else:
            cap = 0.85
    elif review_count <= 4:
        if has_mixed_reviews:
            cap = 0.6
        elif generic_count >= 2:
            cap = 0.65
            flags.add("limited_review_count")
        else:
            cap = 0.9
    else:
        if has_mixed_reviews:
            cap = 0.75
        elif generic_count >= max(1, review_count // 2):
            cap = 0.8

    adjusted_confidence = min(verdict.confidence_score, cap)
    user_warning = verdict.user_warning
    if adjusted_confidence < 0.5 and not user_warning:
        user_warning = "Insufficient evidence to provide a reliable summary."
    elif adjusted_confidence >= 0.5 and user_warning:
        user_warning = None

    return verdict.model_copy(
        update={
            "confidence_score": adjusted_confidence,
            "insufficient_data_flags": sorted(flags),
            "user_warning": user_warning,
        }
    )


def build_repair_prompt(original_prompt: str, raw_output: str, issues):
    issues_text = "\n".join(f"- {issue}" for issue in issues)
    return f"""
You previously returned JSON that failed semantic checks.

Issues to fix:
{issues_text}

Original task:
{original_prompt}

Previous JSON:
{raw_output}

Return a corrected JSON object only.
Keep the schema identical.
Fix the evidence-to-label mapping.
Split mixed claims.
Include all mixed themes in disagreements.
Do not mark a pure negative theme as a disagreement.
Do not use "good quality" for evidence that only shows "easy to use".
If a review says it is easy to use but only the Arabic text expresses that idea, keep the label as "easy to use".
If a review is mixed on quality and ease of use, split those into separate points.
Do not invent new facts.
"""


def normalize_payload(payload: dict) -> dict:
    if payload.get("confidence_score", 1.0) >= 0.5 and payload.get("user_warning"):
        payload = dict(payload)
        payload["user_warning"] = None
    return payload


def generate_verdict_for_reviews(reviews):
    if not reviews:
        raise ValueError("No reviews provided")

    prompt = build_prompt(reviews)

    try:
        raw_output = call_llm(prompt)
        extracted_output = extract_json(raw_output)
    except Exception as exc:
        raise RuntimeError(f"Pipeline failed before validation: {exc}") from exc

    parsed = json.loads(extracted_output)
    parsed = normalize_payload(parsed)
    validated = MomsVerdict.model_validate(parsed)
    validate_against_reviews(validated, reviews)
    validated = calibrate_uncertainty(validated, reviews)
    semantic_issues = validate_semantics(validated, reviews)

    if semantic_issues:
        repair_prompt = build_repair_prompt(prompt, extracted_output, semantic_issues)
        raw_output = call_llm(repair_prompt)
        extracted_output = extract_json(raw_output)
        parsed = json.loads(extracted_output)
        parsed = normalize_payload(parsed)
        validated = MomsVerdict.model_validate(parsed)
        validate_against_reviews(validated, reviews)
        validated = calibrate_uncertainty(validated, reviews)
        semantic_issues = validate_semantics(validated, reviews)
        if semantic_issues:
            raise ValueError(f"Semantic validation failed: {semantic_issues}")

    return validated


def run_pipeline(reviews_path: Path = DEFAULT_REVIEWS_PATH):
    reviews = load_reviews(reviews_path)

    try:
        validated = generate_verdict_for_reviews(reviews)
        print("\nVALID OUTPUT\n")
        print(json.dumps(validated.model_dump(), indent=2, ensure_ascii=False))
        return validated
    except Exception as exc:
        print("\nVALIDATION FAILED\n")
        print("\nError:", str(exc))
        return None


if __name__ == "__main__":
    run_pipeline()
