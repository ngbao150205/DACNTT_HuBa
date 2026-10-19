"""Backend sentiment rules for uncertain predictions from the single AI model."""

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

MODEL_CONFIDENCE_THRESHOLD = 0.8


# ============================================================
# RULE FILE
# ============================================================

RULE_FILE = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "rules"
    / "sentiment_decision_rules.json"
)


def load_sentiment_rules() -> dict[str, Any]:
    """
    Load sentiment decision rules from JSON.

    Expected path:
        backend/app/rules/sentiment_decision_rules.json
    """

    if not RULE_FILE.exists():
        raise FileNotFoundError(
            f"Sentiment rule file not found: {RULE_FILE}"
        )

    with RULE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


SENTIMENT_RULES = load_sentiment_rules()


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    text = str(text).lower()
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_rating(rating: int | float | str | None) -> int | None:
    try:
        if rating is None:
            return None

        value = int(float(rating))
    except Exception:
        return None

    if value < 1 or value > 5:
        return None

    return value


# ============================================================
# RULE HELPERS
# ============================================================

def get_rule_list(key: str) -> list[str]:
    value = SENTIMENT_RULES.get(key, [])

    if not isinstance(value, list):
        return []

    return [
        normalize_text(str(item))
        for item in value
        if normalize_text(str(item))
    ]


def get_rule_int(
    key: str,
    default: int,
) -> int:
    try:
        return int(SENTIMENT_RULES.get(key, default))
    except Exception:
        return default


def contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    text = normalize_text(text)
    phrase = normalize_text(phrase)

    if not text or not phrase:
        return False

    pattern = (
        r"(?<![0-9a-zà-ỹ])"
        + re.escape(phrase)
        + r"(?![0-9a-zà-ỹ])"
    )

    return re.search(pattern, text) is not None


def has_any(
    text: str,
    patterns: list[str],
) -> bool:
    text = normalize_text(text)

    return any(
        contains_phrase(text, pattern)
        for pattern in patterns
    )


def count_matches(
    text: str,
    patterns: list[str],
) -> int:
    text = normalize_text(text)

    return sum(
        1
        for pattern in patterns
        if contains_phrase(text, pattern)
    )


# ============================================================
# EVIDENCE DETECTION
# ============================================================

def is_future_uncertainty_not_negative(text: str) -> bool:
    """
    Detect future uncertainty, not actual negative experience.

    Example:
        "không biết quần có bị bai chun không"
        "dùng lâu mới biết có bền không"
    """

    text = normalize_text(text)

    uncertainty_patterns = get_rule_list(
        "future_uncertainty_patterns"
    )

    future_issue_patterns = get_rule_list(
        "future_issue_patterns"
    )

    has_uncertainty = any(
        contains_phrase(text, pattern)
        for pattern in uncertainty_patterns
    )

    has_future_issue = any(
        contains_phrase(text, pattern)
        for pattern in future_issue_patterns
    )

    return has_uncertainty and has_future_issue


def get_text_evidence(text: str) -> dict[str, Any]:
    text = normalize_text(text)

    positive_evidence = get_rule_list("positive_evidence")
    negative_evidence = get_rule_list("negative_evidence")
    positive_negation_patterns = get_rule_list(
        "positive_negation_patterns"
    )
    negative_phrases = get_rule_list("negative_phrases")
    strong_negative_keywords = get_rule_list(
        "strong_negative_keywords"
    )

    positive_score = count_matches(
        text=text,
        patterns=positive_evidence,
    )

    negative_score = count_matches(
        text=text,
        patterns=negative_evidence,
    )

    has_positive_negation = has_any(
        text=text,
        patterns=positive_negation_patterns,
    )

    has_negative_phrase = has_any(
        text=text,
        patterns=negative_phrases,
    )

    has_strong_negative = has_any(
        text=text,
        patterns=strong_negative_keywords,
    )

    future_uncertainty_not_negative = (
        is_future_uncertainty_not_negative(text)
    )

    if future_uncertainty_not_negative:
        has_strong_negative = False

    return {
        "positive_score": positive_score,
        "negative_score": negative_score,
        "has_positive_negation": has_positive_negation,
        "has_negative_phrase": has_negative_phrase,
        "has_strong_negative": has_strong_negative,
        "future_uncertainty_not_negative": future_uncertainty_not_negative,
    }


def detect_rating_conflict(
    raw_label: str,
    rating: int | None,
) -> bool:
    if rating is None:
        return False

    positive_rating_threshold = get_rule_int(
        "positive_rating_threshold",
        4,
    )

    negative_rating_threshold = get_rule_int(
        "negative_rating_threshold",
        2,
    )

    if raw_label == "Positive" and rating <= negative_rating_threshold:
        return True

    if raw_label == "Negative" and rating >= positive_rating_threshold:
        return True

    return False


def apply_final_guards(
    final_label: str,
    final_confidence: float,
    method: str,
    rating: int | None,
    evidence: dict[str, Any],
) -> tuple[str, float, str]:
    positive_score = evidence["positive_score"]
    negative_score = evidence["negative_score"]
    has_positive_negation = evidence["has_positive_negation"]
    has_negative_phrase = evidence["has_negative_phrase"]
    has_strong_negative = evidence["has_strong_negative"]
    future_uncertainty_not_negative = evidence[
        "future_uncertainty_not_negative"
    ]

    # GUARD 1:
    # "không đau tai", "không bị lỗi", "không rè"
    # must not become Negative.
    if has_positive_negation and final_label == "Negative":
        if not has_negative_phrase:
            return (
                "Positive",
                0.75,
                "positive_negation_override",
            )

    # GUARD 2:
    # High rating but final Negative.
    if rating is not None and rating >= 4 and final_label == "Negative":
        strong_negative = (
            has_negative_phrase
            or (
                has_strong_negative
                and not future_uncertainty_not_negative
                and negative_score >= 2
            )
        )

        if positive_score > negative_score and not strong_negative:
            return (
                "Positive",
                0.75,
                "rating_high_negative_to_positive_guard",
            )

        if not strong_negative:
            return (
                "Neutral",
                0.60,
                "rating_high_negative_conflict_guard",
            )

    # GUARD 3:
    # Low rating but final Positive.
    if rating is not None and rating <= 2 and final_label == "Positive":
        strong_positive = (
            positive_score >= 2
            and negative_score == 0
            and not has_negative_phrase
            and not has_strong_negative
        )

        if not strong_positive:
            return (
                "Negative",
                0.70,
                "rating_low_positive_conflict_guard",
            )

    # GUARD 4:
    # Rating 3 is normally a neutral zone unless text evidence is clear.
    if rating == 3:
        if has_negative_phrase or (
            negative_score > positive_score
            and has_strong_negative
        ):
            return (
                "Negative",
                max(final_confidence, 0.65),
                "rating_3_negative_text",
            )

        if positive_score > negative_score:
            return (
                "Positive",
                max(final_confidence, 0.65),
                "rating_3_positive_text",
            )

        return (
            "Neutral",
            0.60,
            "rating_3_default_neutral",
        )

    return (
        final_label,
        final_confidence,
        method,
    )


def decide_result(
    text: str,
    rating: int | float | None,
    model_result: dict[str, Any],
) -> dict[str, Any]:
    """Accept confidence >= 0.8 directly; otherwise apply the existing guards."""
    if not isinstance(model_result, dict):
        raise ValueError("AI model result must be a dictionary")
    raw_label = model_result.get("sentiment") or model_result.get("label")
    if raw_label not in {"Positive", "Negative", "Neutral"}:
        raise ValueError("AI model result has an invalid sentiment")
    try:
        raw_confidence = float(model_result["confidence"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("AI model result has an invalid confidence") from error
    if not math.isfinite(raw_confidence) or not 0 <= raw_confidence <= 1:
        raise ValueError("AI model confidence must be between 0 and 1")

    result = {
        "sentiment": raw_label,
        "confidence": raw_confidence,
        "model_name": model_result.get("model_name", "underthesea_bilstm_custom_vocab_v3"),
        "raw_sentiment": raw_label,
        "raw_confidence": raw_confidence,
        "confidence_threshold": MODEL_CONFIDENCE_THRESHOLD,
        "rules_applied": False,
        "method": "model_high_confidence",
        "decision_method": "model_high_confidence",
    }
    # Check the unrounded model confidence, including exactly 0.8.
    if raw_confidence >= MODEL_CONFIDENCE_THRESHOLD:
        return result

    normalized_rating = normalize_rating(rating)
    evidence = get_text_evidence(normalize_text(text))
    label, confidence, method = apply_final_guards(
        final_label=raw_label,
        final_confidence=raw_confidence,
        method="model_low_confidence_no_override",
        rating=normalized_rating,
        evidence=evidence,
    )
    return {
        **result,
        "sentiment": label,
        "confidence": confidence,
        "method": method,
        "decision_method": method,
        "rules_applied": True,
        "rating_conflict": detect_rating_conflict(raw_label, normalized_rating),
        "evidence": evidence,
    }


