import json
import re
import unicodedata

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.database.models import RiskDetection


# ============================================================
# RULE FILE
# ============================================================

RULE_FILE = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "rules"
    / "risk_rules.json"
)


def load_risk_rules() -> dict[str, Any]:
    """
    Load risk detection rules from JSON file.

    Rule file path:
        backend/app/rules/risk_rules.json
    """

    if not RULE_FILE.exists():
        raise FileNotFoundError(
            f"Risk rule file not found: {RULE_FILE}"
        )

    with RULE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


RISK_RULES = load_risk_rules()


# ============================================================
# RULE ACCESSORS
# ============================================================

def get_rule_list(key: str) -> list[str]:
    """
    Safely get a list from risk_rules.json.
    """

    value = RISK_RULES.get(key, [])

    if not isinstance(value, list):
        return []

    return [
        str(item)
        for item in value
        if str(item).strip()
    ]


def get_rule_dict(key: str) -> dict[str, str]:
    """
    Safely get a dictionary from risk_rules.json.
    """

    value = RISK_RULES.get(key, {})

    if not isinstance(value, dict):
        return {}

    return {
        str(old): str(new)
        for old, new in value.items()
    }


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text: str | None) -> str:
    """
    Normalize Vietnamese review text before risk detection.
    """

    if not text:
        return ""

    text = str(text).lower()
    text = unicodedata.normalize("NFC", text)

    abbreviations = get_rule_dict("abbreviations")

    for old, new in sorted(
        abbreviations.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        text = re.sub(
            rf"(?<![0-9a-zà-ỹ]){re.escape(old)}(?![0-9a-zà-ỹ])",
            new,
            text,
        )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_sentiment(sentiment: str | None) -> str | None:
    """
    Normalize sentiment label.
    """

    if not sentiment:
        return None

    value = str(sentiment).strip().lower()

    mapping = {
        "positive": "Positive",
        "tích cực": "Positive",

        "neutral": "Neutral",
        "trung lập": "Neutral",

        "negative": "Negative",
        "tiêu cực": "Negative",
    }

    return mapping.get(value)


def normalize_rating(rating: int | float | None) -> int | None:
    """
    Normalize rating safely.
    """

    if rating is None:
        return None

    try:
        return int(rating)
    except (TypeError, ValueError):
        return None


# ============================================================
# KEYWORD MATCHING
# ============================================================

def contains_keyword(text: str, keyword: str) -> bool:
    """
    Match keyword with Vietnamese word boundaries.

    Avoid false matches:
        "giả" in "đánh giá"
        "hư" in "như"
    """

    if not text or not keyword:
        return False

    normalized_keyword = normalize_text(keyword)

    if not normalized_keyword:
        return False

    pattern = (
        r"(?<![0-9a-zà-ỹ])"
        + re.escape(normalized_keyword)
        + r"(?![0-9a-zà-ỹ])"
    )

    return re.search(pattern, text) is not None


def split_sentences(text: str) -> list[str]:
    """
    Split review into short clauses.
    """

    parts = re.split(r"[.!?;,\n\r]+", text)

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def find_matching_sentence(text: str, keyword: str) -> str | None:
    """
    Find the sentence or clause that contains keyword.
    """

    for sentence in split_sentences(text):
        if contains_keyword(sentence, keyword):
            return sentence

    return None


def get_keyword_clause(sentence: str, keyword: str) -> str:
    """
    Get local clause containing keyword.

    Example:
        "sản phẩm tốt nhưng hộp bị móp"

    With keyword:
        "móp"

    Only check:
        "hộp bị móp"
    """

    connectors = [
        "nhưng mà",
        "tuy nhiên",
        "mặc dù",
        "nhưng",
        "dù",
        "tuy",
        "mà",
        "còn",
    ]

    pattern = r"\b(?:" + "|".join(re.escape(item) for item in connectors) + r")\b"

    parts = re.split(pattern, sentence)

    for part in parts:
        if contains_keyword(part, keyword):
            return part.strip()

    return sentence.strip()


# ============================================================
# CONTEXT CHECKING
# ============================================================

def is_negated(sentence: str, keyword: str) -> bool:
    """
    Detect negated risk keyword.

    Examples:
        không móp
        không bị móp
        không có lỗi
        không gặp vấn đề
        chưa hỏng
    """

    if not sentence or not keyword:
        return False

    normalized_keyword = normalize_text(keyword)

    if not normalized_keyword:
        return False

    negation_words = get_rule_list("negation_words")

    if not negation_words:
        negation_words = [
            "không",
            "chưa",
            "chẳng",
            "chả",
            "ko",
            "k",
            "hok",
            "hông",
        ]

    pattern = (
        r"(?<![0-9a-zà-ỹ])"
        r"(?:"
        + "|".join(re.escape(word) for word in negation_words)
        + r")"
        r"\s+(?:bị\s+|có\s+|hề\s+|gặp\s+|thấy\s+)?"
        + re.escape(normalized_keyword)
        + r"(?![0-9a-zà-ỹ])"
    )

    return re.search(pattern, sentence) is not None


def has_positive_context(sentence: str, keyword: str) -> bool:
    """
    Check whether keyword appears in a positive or negated context.
    """

    clause = get_keyword_clause(sentence, keyword)

    if is_negated(clause, keyword):
        return True

    normalized_keyword = normalize_text(keyword)

    keyword_position = clause.find(normalized_keyword)

    if keyword_position == -1:
        return False

    start = max(0, keyword_position - 40)
    end = min(
        len(clause),
        keyword_position + len(normalized_keyword) + 40,
    )

    local_context = clause[start:end]

    positive_phrases = [
        normalize_text(item)
        for item in get_rule_list("positive_phrases")
    ]

    for phrase in positive_phrases:
        if not phrase:
            continue

        if phrase == normalized_keyword:
            continue

        # Avoid suppressing serious negative phrases:
        # keyword: "không chính hãng"
        # positive phrase: "chính hãng"
        if phrase in normalized_keyword:
            continue

        if normalized_keyword in phrase:
            continue

        if phrase in local_context:
            return True

    return False


def has_negative_context(sentence: str, keyword: str) -> bool:
    """
    Check whether keyword is used as a real complaint.
    """

    clause = get_keyword_clause(sentence, keyword)

    if is_negated(clause, keyword):
        return False

    normalized_keyword = normalize_text(keyword)

    # Long phrases are considered explicit risk signals.
    if len(normalized_keyword.split()) >= 2:
        return True

    negative_markers = [
        normalize_text(item)
        for item in get_rule_list("negative_markers")
    ]

    for marker in negative_markers:
        if not marker:
            continue

        if marker == normalized_keyword:
            continue

        if contains_keyword(clause, marker):
            return True

    return True


# ============================================================
# RISK BUSINESS LOGIC
# ============================================================

def should_check_medium_risk(
    sentiment: str | None,
    rating: int | float | None = None,
) -> bool:
    """
    Decide whether MEDIUM risk should be checked.

    Business rule:
        Neutral / Negative
            -> check MEDIUM

        Missing sentiment + rating <= 2
            -> check MEDIUM

        Positive
            -> skip MEDIUM

        Missing sentiment + rating >= 4
            -> skip MEDIUM
    """

    normalized_sentiment = normalize_sentiment(sentiment)
    normalized_rating = normalize_rating(rating)

    if normalized_sentiment in {"Neutral", "Negative"}:
        return True

    if normalized_sentiment == "Positive":
        return False

    if normalized_rating is not None and normalized_rating <= 2:
        return True

    return False


# ============================================================
# DETECT RISK
# ============================================================

def detect_risk(
    content: str,
    sentiment: str | None = None,
    rating: int | float | None = None,
) -> dict:
    """
    Detect risk from review.

    Business rule:
        HIGH risk:
            - Always check, even when sentiment is Positive.

        MEDIUM risk:
            - Only check when sentiment is Neutral / Negative.
            - Also check when sentiment is missing and rating <= 2.

        LOW:
            - Default safe state.
            - risk_flag = False.
            - Frontend must not display "Phát hiện rủi ro" when risk_flag is False.
    """

    text = normalize_text(content)

    if not text:
        return {
            "risk_flag": False,
            "risk_level": "LOW",
            "risk_keyword": None,
        }

    high_risk_keywords = sorted(
        {
            normalize_text(keyword)
            for keyword in get_rule_list("high_risk_keywords")
        },
        key=len,
        reverse=True,
    )

    medium_risk_keywords = sorted(
        {
            normalize_text(keyword)
            for keyword in get_rule_list("medium_risk_keywords")
        },
        key=len,
        reverse=True,
    )

    # ========================================================
    # 1. HIGH RISK
    # ========================================================
    # HIGH risk is serious enough to be detected even in a
    # Positive review.
    #
    # Example:
    #   "Hàng Fake, chắc chắn đây là hàng fake."
    # ========================================================

    for keyword in high_risk_keywords:
        if not keyword:
            continue

        if not contains_keyword(text, keyword):
            continue

        sentence = (
            find_matching_sentence(text, keyword)
            or text
        )

        if has_positive_context(sentence, keyword):
            continue

        return {
            "risk_flag": True,
            "risk_level": "HIGH",
            "risk_keyword": keyword,
        }

    # ========================================================
    # 2. MEDIUM RISK GATE
    # ========================================================
    # Positive reviews skip MEDIUM risk to reduce noise.
    # ========================================================

    if not should_check_medium_risk(
        sentiment=sentiment,
        rating=rating,
    ):
        return {
            "risk_flag": False,
            "risk_level": "LOW",
            "risk_keyword": None,
        }

    # ========================================================
    # 3. MEDIUM RISK
    # ========================================================
    # Only Neutral / Negative / unknown-low-rating reviews reach here.
    # ========================================================

    for keyword in medium_risk_keywords:
        if not keyword:
            continue

        if not contains_keyword(text, keyword):
            continue

        sentence = (
            find_matching_sentence(text, keyword)
            or text
        )

        if has_positive_context(sentence, keyword):
            continue

        if not has_negative_context(sentence, keyword):
            continue

        return {
            "risk_flag": True,
            "risk_level": "MEDIUM",
            "risk_keyword": keyword,
        }

    # ========================================================
    # 4. NO RISK
    # ========================================================
    # Negative sentiment alone is not risk.
    # Low rating alone is also not risk.
    # ========================================================

    return {
        "risk_flag": False,
        "risk_level": "LOW",
        "risk_keyword": None,
    }


# ============================================================
# SAVE RISK
# ============================================================

def save_risk_detection(
    db: Session,
    review_id: int,
    content: str,
    sentiment: str | None = None,
    rating: int | float | None = None,
) -> RiskDetection:
    """
    Save or update risk detection for one review.
    """

    result = detect_risk(
        content=content,
        sentiment=sentiment,
        rating=rating,
    )

    risk = (
        db.query(RiskDetection)
        .filter(RiskDetection.review_id == review_id)
        .first()
    )

    if risk is None:
        risk = RiskDetection(
            review_id=review_id,
            risk_flag=result["risk_flag"],
            risk_level=result["risk_level"],
            risk_keyword=result["risk_keyword"],
        )

        db.add(risk)

    else:
        risk.risk_flag = result["risk_flag"]
        risk.risk_level = result["risk_level"]
        risk.risk_keyword = result["risk_keyword"]

    db.flush()

    return risk