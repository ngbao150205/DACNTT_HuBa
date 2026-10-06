import json
import re
import unicodedata

from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import (
    Product,
    Review,
    IssueAnalysis,
)


# ============================================================
# RULE FILE
# ============================================================

RULE_FILE = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "rules"
    / "issue_rules.json"
)


def load_issue_rules() -> dict[str, Any]:
    """
    Load issue rules from JSON file.

    Rule file path:
        backend/app/rules/issue_rules.json
    """

    if not RULE_FILE.exists():
        raise FileNotFoundError(
            f"Issue rule file not found: {RULE_FILE}"
        )

    with RULE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


ISSUE_RULES = load_issue_rules()


# ============================================================
# CONSTANTS
# ============================================================

PRODUCT_QUALITY = "PRODUCT_QUALITY"
SHIPPING_LOGISTICS = "SHIPPING_LOGISTICS"
CUSTOMER_SERVICE_RETURNS = "CUSTOMER_SERVICE_RETURNS"
PRICING_PROMOTIONS = "PRICING_PROMOTIONS"

VALID_ISSUE_TYPES = {
    PRODUCT_QUALITY,
    SHIPPING_LOGISTICS,
    CUSTOMER_SERVICE_RETURNS,
    PRICING_PROMOTIONS,
}

PRODUCT_GROUP_MAPPING = {
    "FMCG": "FMCG_BEAUTY_HEALTH",
    "COSMETIC": "FMCG_BEAUTY_HEALTH",

    "PHONE": "ELECTRONICS_TECH",
    "EARPHONE": "ELECTRONICS_TECH",

    "CLOTHING": "FASHION_ACCESSORIES",
    "JEWELRY": "FASHION_ACCESSORIES",
    "PACKAGING": "FASHION_ACCESSORIES",
}

ISSUE_LABELS = {
    PRODUCT_QUALITY: "Chất lượng sản phẩm",
    SHIPPING_LOGISTICS: "Giao hàng và vận chuyển",
    CUSTOMER_SERVICE_RETURNS: "Dịch vụ khách hàng và đổi trả",
    PRICING_PROMOTIONS: "Giá cả và khuyến mãi",
}


# ============================================================
# SCORING CONFIG
# ============================================================

STRONG_SCORE = 4
MEDIUM_SCORE = 2
WEAK_SCORE = 1

NEGATIVE_BONUS = 1
LOW_RATING_BONUS = 1

MIN_ISSUE_SCORE = 3

FALLBACK_SCORE = 1


# ============================================================
# CRITICAL KEYWORDS
# ============================================================

CRITICAL_ISSUE_KEYWORDS = [
    "hàng fake",
    "hàng giả",
    "hàng nhái",
    "không chính hãng",
    "không phải hàng chính hãng",
    "sản phẩm giả",
    "giả mạo",
    "hết hạn",
    "quá hạn",
    "dị ứng",
    "kích ứng",
    "ngộ độc",
    "không dùng được",
    "không sử dụng được",
    "lừa đảo",
    "treo đầu dê bán thịt chó",
]


# ============================================================
# BUILT-IN CONTEXT RULES
# ============================================================

BUILTIN_STRONG_KEYWORDS = {
    PRODUCT_QUALITY: [
        "chất lượng rất tệ",
        "chất lượng tệ",
        "chất lượng kém",
        "sản phẩm lỗi",
        "sản phẩm bị lỗi",
        "bị lỗi",
        "bị hỏng",
        "bị hư",
        "không dùng được",
        "không sử dụng được",
        "dùng được vài ngày",
        "sử dụng được vài ngày",
        "mới dùng đã hỏng",
        "mới dùng đã lỗi",
        "nhanh hỏng",
        "không bền",
        "fake",
        "hàng fake",
        "hàng giả",
        "hàng nhái",
        "không chính hãng",
        "không phải hàng chính hãng",
        "sai mô tả",
        "không giống hình",
        "khác hình",
        "khác mô tả",
        "không đúng mẫu",
        "không đúng màu",
        "không đúng size",
    ],

    SHIPPING_LOGISTICS: [
        "giao hàng chậm",
        "ship chậm",
        "giao lâu",
        "ship lâu",
        "giao trễ",
        "ship trễ",
        "chưa nhận được hàng",
        "không nhận được hàng",
        "thất lạc",
        "giao nhầm",
        "giao sai",
        "giao thiếu",
        "thiếu hàng",
        "đơn bị hủy",
        "hủy đơn",
    ],

    CUSTOMER_SERVICE_RETURNS: [
        "shop không phản hồi",
        "không phản hồi",
        "không hỗ trợ",
        "hỗ trợ kém",
        "từ chối bảo hành",
        "không bảo hành",
        "bảo hành lâu",
        "bảo hành không được",
        "không cho đổi trả",
        "không đổi trả",
        "không hoàn tiền",
        "hoàn tiền lâu",
        "shop không xử lý",
        "không xử lý",
        "chăm sóc khách hàng kém",
    ],

    PRICING_PROMOTIONS: [
        "không đáng tiền",
        "phí tiền",
        "uổng tiền",
        "giá quá cao",
        "giá cao",
        "giá mắc",
        "giá đắt",
        "đắt so với chất lượng",
        "mắc so với chất lượng",
        "không áp được mã",
        "không được giảm giá",
        "giá thay đổi",
        "đội giá",
    ],
}

BUILTIN_WEAK_KEYWORDS = {
    PRODUCT_QUALITY: [
        "sản phẩm",
        "hàng",
        "sp",
    ],

    SHIPPING_LOGISTICS: [
        "giao",
        "ship",
        "vận chuyển",
        "đơn hàng",
        "nhận hàng",
    ],

    CUSTOMER_SERVICE_RETURNS: [
        "shop",
        "người bán",
        "seller",
        "hỗ trợ",
        "tư vấn",
        "phản hồi",
        "bảo hành",
        "đổi trả",
        "đổi hàng",
        "trả hàng",
        "hoàn tiền",
        "khiếu nại",
    ],

    PRICING_PROMOTIONS: [
        "giá",
        "đắt",
        "mắc",
        "rẻ",
        "khuyến mãi",
        "sale",
        "voucher",
        "mã giảm giá",
        "giảm giá",
        "hoàn xu",
        "cashback",
        "tiền",
    ],
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text: str | None) -> str:
    """
    Normalize Vietnamese review text before keyword matching.
    """

    if not text:
        return ""

    text = str(text).lower()
    text = unicodedata.normalize("NFC", text)

    abbreviations = ISSUE_RULES.get("abbreviations", {})

    if isinstance(abbreviations, dict):
        for old, new in sorted(
            abbreviations.items(),
            key=lambda item: len(str(item[0])),
            reverse=True,
        ):
            old_value = normalize_text_without_abbreviation(str(old))
            new_value = normalize_text_without_abbreviation(str(new))

            if not old_value:
                continue

            text = re.sub(
                rf"(?<![0-9a-zà-ỹ]){re.escape(old_value)}(?![0-9a-zà-ỹ])",
                new_value,
                text,
            )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_text_without_abbreviation(text: str | None) -> str:
    if not text:
        return ""

    text = str(text).lower()
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_sentiment(sentiment: str | None) -> str | None:
    """
    Normalize sentiment label to:
        Positive
        Neutral
        Negative
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


def normalize_product_group(category: str | None) -> str:
    """
    Map raw product category into one of the three business groups.
    """

    if not category:
        return "GENERAL"

    normalized = (
        str(category)
        .strip()
        .upper()
        .replace(" ", "_")
        .replace("-", "_")
    )

    return PRODUCT_GROUP_MAPPING.get(normalized, "GENERAL")


def normalize_rating(rating: int | float | None) -> int | None:
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
        "hư" inside "như"
        "giả" inside "đánh giá"
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
    Split review into clauses.
    """

    parts = re.split(r"[.!?;,\n\r]+", text)

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def find_matching_sentence(text: str, keyword: str) -> str | None:
    for sentence in split_sentences(text):
        if contains_keyword(sentence, keyword):
            return sentence

    return None


def get_keyword_clause(sentence: str, keyword: str) -> str:
    """
    Get the local clause containing the keyword.
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

    pattern = (
        r"\b(?:"
        + "|".join(re.escape(item) for item in connectors)
        + r")\b"
    )

    parts = re.split(pattern, sentence)

    for part in parts:
        if contains_keyword(part, keyword):
            return part.strip()

    return sentence.strip()


# ============================================================
# CONTEXT CHECKING
# ============================================================

def is_negated(clause: str, keyword: str) -> bool:
    """
    Detect negated issue keyword.

    Examples:
        không móp
        không bị móp
        không có lỗi
        chưa bị hỏng
    """

    if not clause or not keyword:
        return False

    negation_words = ISSUE_RULES.get(
        "negation_words",
        [
            "không",
            "ko",
            "k",
            "kh",
            "chưa",
            "chẳng",
            "chả",
        ],
    )

    if not isinstance(negation_words, list):
        negation_words = [
            "không",
            "ko",
            "k",
            "kh",
            "chưa",
            "chẳng",
            "chả",
        ]

    normalized_keyword = normalize_text(keyword)

    pattern = (
        r"(?<![0-9a-zà-ỹ])"
        r"(?:"
        + "|".join(re.escape(str(word)) for word in negation_words)
        + r")"
        r"\s+(?:bị\s+|có\s+|hề\s+|gặp\s+|thấy\s+)?"
        + re.escape(normalized_keyword)
        + r"(?![0-9a-zà-ỹ])"
    )

    return re.search(pattern, clause) is not None


def has_positive_context(sentence: str, keyword: str) -> bool:
    """
    Check whether keyword appears in positive or negated context.
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

    positive_phrases = ISSUE_RULES.get(
        "positive_phrases",
        [],
    )

    if not isinstance(positive_phrases, list):
        return False

    for phrase in positive_phrases:
        normalized_phrase = normalize_text(str(phrase))

        if not normalized_phrase:
            continue

        if normalized_phrase == normalized_keyword:
            continue

        if normalized_phrase in normalized_keyword:
            continue

        if normalized_keyword in normalized_phrase:
            continue

        if normalized_phrase in local_context:
            return True

    return False


def has_negative_context(sentence: str, keyword: str) -> bool:
    """
    Check whether keyword is used as a real complaint.
    """

    clause = get_keyword_clause(sentence, keyword)

    if is_negated(clause, keyword):
        return False

    negative_markers = ISSUE_RULES.get(
        "negative_markers",
        [],
    )

    if isinstance(negative_markers, list):
        for marker in negative_markers:
            normalized_marker = normalize_text(str(marker))

            if not normalized_marker:
                continue

            if normalized_marker == normalize_text(keyword):
                continue

            if contains_keyword(clause, normalized_marker):
                return True

    if len(normalize_text(keyword).split()) >= 2:
        return True

    return True


def is_reported_complaint_but_self_positive(
    text: str,
    sentence: str,
) -> bool:
    """
    Ignore cases where user only refers to other people's complaints
    but says their own received product is fine.
    """

    reported_markers = ISSUE_RULES.get(
        "reported_complaint_markers",
        [],
    )

    self_positive_markers = ISSUE_RULES.get(
        "self_positive_markers",
        [],
    )

    if not isinstance(reported_markers, list):
        reported_markers = []

    if not isinstance(self_positive_markers, list):
        self_positive_markers = []

    has_reported_marker = any(
        normalize_text(str(marker)) in text
        for marker in reported_markers
    ) or any(
        normalize_text(str(marker)) in sentence
        for marker in reported_markers
    )

    has_self_positive_marker = any(
        normalize_text(str(marker)) in text
        for marker in self_positive_markers
    )

    return has_reported_marker and has_self_positive_marker


# ============================================================
# CHECKING CONDITIONS
# ============================================================

def has_critical_issue_keyword(text: str) -> bool:
    """
    Critical issue keywords should still trigger issue detection even if
    sentiment model predicts Positive.
    """

    for keyword in CRITICAL_ISSUE_KEYWORDS:
        normalized_keyword = normalize_text(keyword)

        if contains_keyword(text, normalized_keyword):
            return True

    return False


def should_check_issue(
    text: str,
    sentiment: str | None,
    rating: int | float | None = None,
) -> bool:
    """
    Decide whether a review should be checked for issues.
    """

    normalized_sentiment = normalize_sentiment(sentiment)
    normalized_rating = normalize_rating(rating)

    if normalized_sentiment in {"Neutral", "Negative"}:
        return True

    if normalized_rating is not None and normalized_rating <= 2:
        return True

    if has_critical_issue_keyword(text):
        return True

    return False


def should_force_issue_from_sentiment(
    sentiment: str | None,
    rating: int | float | None = None,
) -> bool:
    """
    Force issue creation when sentiment is Negative or rating <= 2.
    """

    normalized_sentiment = normalize_sentiment(sentiment)
    normalized_rating = normalize_rating(rating)

    if normalized_sentiment == "Negative":
        return True

    if normalized_rating is not None and normalized_rating <= 2:
        return True

    return False


# ============================================================
# RULE MERGING
# ============================================================

def merge_rule_group(
    rules: dict[str, list[str]],
    source: Any,
) -> None:
    """
    Merge one rule group into the final rules dictionary.

    Only the four standardized issue types are accepted.
    """

    if not isinstance(source, dict):
        return

    for issue_type, keywords in source.items():
        normalized_issue_type = str(issue_type).upper()

        if normalized_issue_type not in VALID_ISSUE_TYPES:
            continue

        if not isinstance(keywords, list):
            continue

        rules.setdefault(normalized_issue_type, [])
        rules[normalized_issue_type].extend(keywords)


def get_keywords_for_category(category: str | None) -> dict[str, list[str]]:
    """
    Build keyword rules for a product.

    Final rule set:
        GENERAL
        + product group rule
    """

    rules: dict[str, list[str]] = {}

    general_rules = ISSUE_RULES.get("GENERAL", {})
    merge_rule_group(rules, general_rules)

    product_group = normalize_product_group(category)
    group_rules = ISSUE_RULES.get(product_group, {})
    merge_rule_group(rules, group_rules)

    cleaned_rules: dict[str, list[str]] = {}

    for issue_type, keywords in rules.items():
        unique_keywords = sorted(
            {
                normalize_text(str(keyword))
                for keyword in keywords
                if normalize_text(str(keyword))
            },
            key=len,
            reverse=True,
        )

        cleaned_rules[issue_type] = unique_keywords

    return cleaned_rules


# ============================================================
# SCORING HELPERS
# ============================================================

def keyword_score(keyword: str) -> int:
    """
    Infer score level from keyword length and explicit phrase strength.

    Long phrases are usually stronger issue indicators:
        "giao hàng chậm"
        "chất lượng rất tệ"
        "không chính hãng"
        "không hoàn tiền"
    """

    normalized_keyword = normalize_text(keyword)

    if not normalized_keyword:
        return 0

    words = normalized_keyword.split()

    if len(words) >= 3:
        return STRONG_SCORE

    if len(words) == 2:
        return MEDIUM_SCORE

    return WEAK_SCORE


def add_score(
    scores: dict[str, int],
    matched_keywords: dict[str, list[str]],
    issue_type: str,
    keyword: str,
    score: int,
) -> None:
    if issue_type not in VALID_ISSUE_TYPES:
        return

    if score <= 0:
        return

    scores[issue_type] = scores.get(issue_type, 0) + score

    if keyword not in matched_keywords.setdefault(issue_type, []):
        matched_keywords[issue_type].append(keyword)


def apply_builtin_scoring(
    text: str,
    scores: dict[str, int],
    matched_keywords: dict[str, list[str]],
) -> None:
    """
    Apply built-in scoring rules independent of JSON rule file.
    """

    for issue_type, keywords in BUILTIN_STRONG_KEYWORDS.items():
        for keyword in keywords:
            normalized_keyword = normalize_text(keyword)

            if contains_keyword(text, normalized_keyword):
                add_score(
                    scores=scores,
                    matched_keywords=matched_keywords,
                    issue_type=issue_type,
                    keyword=normalized_keyword,
                    score=STRONG_SCORE,
                )

    for issue_type, keywords in BUILTIN_WEAK_KEYWORDS.items():
        for keyword in keywords:
            normalized_keyword = normalize_text(keyword)

            if contains_keyword(text, normalized_keyword):
                add_score(
                    scores=scores,
                    matched_keywords=matched_keywords,
                    issue_type=issue_type,
                    keyword=normalized_keyword,
                    score=WEAK_SCORE,
                )


def apply_json_rule_scoring(
    text: str,
    category: str | None,
    scores: dict[str, int],
    matched_keywords: dict[str, list[str]],
) -> None:
    """
    Apply keyword rules from issue_rules.json.

    The JSON rule file remains the main configurable rule source.
    """

    category_keywords = get_keywords_for_category(category)

    for issue_type, keywords in category_keywords.items():
        for keyword in keywords:
            if not contains_keyword(text, keyword):
                continue

            sentence = find_matching_sentence(
                text=text,
                keyword=keyword,
            )

            if not sentence:
                continue

            if is_reported_complaint_but_self_positive(
                text=text,
                sentence=sentence,
            ):
                continue

            if has_positive_context(
                sentence=sentence,
                keyword=keyword,
            ):
                continue

            if not has_negative_context(
                sentence=sentence,
                keyword=keyword,
            ):
                continue

            add_score(
                scores=scores,
                matched_keywords=matched_keywords,
                issue_type=issue_type,
                keyword=keyword,
                score=keyword_score(keyword),
            )


def apply_sentiment_rating_bonus(
    scores: dict[str, int],
    sentiment: str | None,
    rating: int | float | None,
) -> None:
    normalized_sentiment = normalize_sentiment(sentiment)
    normalized_rating = normalize_rating(rating)

    has_negative_signal = normalized_sentiment == "Negative"
    has_low_rating = (
        normalized_rating is not None
        and normalized_rating <= 2
    )

    for issue_type in list(scores.keys()):
        if scores[issue_type] <= 0:
            continue

        if has_negative_signal:
            scores[issue_type] += NEGATIVE_BONUS

        if has_low_rating:
            scores[issue_type] += LOW_RATING_BONUS


def apply_context_adjustments(
    text: str,
    scores: dict[str, int],
    matched_keywords: dict[str, list[str]],
) -> None:
    """
    Context-aware adjustment to prevent single keywords from dominating.

    Example:
        "chất lượng rất tệ, phải bảo hành nhiều lần"
        -> PRODUCT_QUALITY should dominate.
    """

    quality_context_keywords = [
        "chất lượng tệ",
        "chất lượng rất tệ",
        "chất lượng kém",
        "sản phẩm lỗi",
        "bị lỗi",
        "bị hỏng",
        "bị hư",
        "không dùng được",
        "không sử dụng được",
        "dùng được vài ngày",
        "sử dụng được vài ngày",
        "nhanh hỏng",
    ]

    warranty_context_keywords = [
        "bảo hành",
        "bảo hành nhiều lần",
        "bảo hành rất nhiều lần",
    ]

    has_quality_context = any(
        contains_keyword(text, normalize_text(keyword))
        for keyword in quality_context_keywords
    )

    has_warranty_context = any(
        contains_keyword(text, normalize_text(keyword))
        for keyword in warranty_context_keywords
    )

    if has_quality_context and has_warranty_context:
        add_score(
            scores=scores,
            matched_keywords=matched_keywords,
            issue_type=PRODUCT_QUALITY,
            keyword="quality_warranty_context",
            score=STRONG_SCORE,
        )

        if scores.get(CUSTOMER_SERVICE_RETURNS, 0) > 0:
            scores[CUSTOMER_SERVICE_RETURNS] = max(
                0,
                scores[CUSTOMER_SERVICE_RETURNS] - WEAK_SCORE,
            )

    service_context_keywords = [
        "không bảo hành",
        "từ chối bảo hành",
        "bảo hành lâu",
        "bảo hành không được",
        "shop không hỗ trợ",
        "shop không phản hồi",
        "không hoàn tiền",
        "không cho đổi trả",
    ]

    has_service_context = any(
        contains_keyword(text, normalize_text(keyword))
        for keyword in service_context_keywords
    )

    if has_service_context:
        add_score(
            scores=scores,
            matched_keywords=matched_keywords,
            issue_type=CUSTOMER_SERVICE_RETURNS,
            keyword="service_return_context",
            score=STRONG_SCORE,
        )

    shipping_service_context_keywords = [
        "giao thiếu",
        "giao sai",
        "giao nhầm",
        "không nhận được hàng",
        "chưa nhận được hàng",
    ]

    has_shipping_context = any(
        contains_keyword(text, normalize_text(keyword))
        for keyword in shipping_service_context_keywords
    )

    if has_shipping_context:
        add_score(
            scores=scores,
            matched_keywords=matched_keywords,
            issue_type=SHIPPING_LOGISTICS,
            keyword="shipping_context",
            score=STRONG_SCORE,
        )

    pricing_quality_context_keywords = [
        "không đáng tiền",
        "đắt so với chất lượng",
        "mắc so với chất lượng",
        "phí tiền",
        "uổng tiền",
    ]

    has_pricing_quality_context = any(
        contains_keyword(text, normalize_text(keyword))
        for keyword in pricing_quality_context_keywords
    )

    if has_pricing_quality_context:
        add_score(
            scores=scores,
            matched_keywords=matched_keywords,
            issue_type=PRICING_PROMOTIONS,
            keyword="pricing_quality_context",
            score=STRONG_SCORE,
        )


def initialize_issue_scores() -> tuple[dict[str, int], dict[str, list[str]]]:
    scores = {
        PRODUCT_QUALITY: 0,
        SHIPPING_LOGISTICS: 0,
        CUSTOMER_SERVICE_RETURNS: 0,
        PRICING_PROMOTIONS: 0,
    }

    matched_keywords = {
        PRODUCT_QUALITY: [],
        SHIPPING_LOGISTICS: [],
        CUSTOMER_SERVICE_RETURNS: [],
        PRICING_PROMOTIONS: [],
    }

    return scores, matched_keywords


def score_issues(
    content: str,
    sentiment: str | None = None,
    category: str | None = "GENERAL",
    rating: int | float | None = None,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    text = normalize_text(content)

    scores, matched_keywords = initialize_issue_scores()

    apply_builtin_scoring(
        text=text,
        scores=scores,
        matched_keywords=matched_keywords,
    )

    apply_json_rule_scoring(
        text=text,
        category=category,
        scores=scores,
        matched_keywords=matched_keywords,
    )

    apply_context_adjustments(
        text=text,
        scores=scores,
        matched_keywords=matched_keywords,
    )

    apply_sentiment_rating_bonus(
        scores=scores,
        sentiment=sentiment,
        rating=rating,
    )

    return scores, matched_keywords


# ============================================================
# FALLBACK ISSUE
# ============================================================

def infer_fallback_issue_type(text: str) -> str:
    """
    Infer one issue type when a Negative review does not match explicit issue.

    Fallback markers are loaded from issue_rules.json:

        fallback_markers.PRODUCT_QUALITY
        fallback_markers.SHIPPING_LOGISTICS
        fallback_markers.CUSTOMER_SERVICE_RETURNS
        fallback_markers.PRICING_PROMOTIONS

    Priority:
        1. PRODUCT_QUALITY
        2. SHIPPING_LOGISTICS
        3. CUSTOMER_SERVICE_RETURNS
        4. PRICING_PROMOTIONS
        5. PRODUCT_QUALITY default
    """

    fallback_markers = ISSUE_RULES.get("fallback_markers", {})

    if not isinstance(fallback_markers, dict):
        fallback_markers = {}

    priority_order = [
        PRODUCT_QUALITY,
        SHIPPING_LOGISTICS,
        CUSTOMER_SERVICE_RETURNS,
        PRICING_PROMOTIONS,
    ]

    for issue_type in priority_order:
        markers = fallback_markers.get(issue_type, [])

        if not isinstance(markers, list):
            continue

        for marker in markers:
            normalized_marker = normalize_text(str(marker))

            if not normalized_marker:
                continue

            if contains_keyword(text, normalized_marker):
                return issue_type

    return PRODUCT_QUALITY


# ============================================================
# DETECT ISSUES
# ============================================================

def detect_issues(
    content: str,
    sentiment: str | None = None,
    category: str | None = "GENERAL",
    rating: int | float | None = None,
) -> list[dict[str, Any]]:
    """
    Detect issues from a review using score-based multi-label detection.

    Output:
        [
            {
                "issue_type": "PRODUCT_QUALITY",
                "matched_keyword": "chất lượng tệ, dùng được vài ngày",
                "score": 9
            },
            ...
        ]
    """

    text = normalize_text(content)

    if not text:
        return []

    if not should_check_issue(
        text=text,
        sentiment=sentiment,
        rating=rating,
    ):
        return []

    scores, matched_keywords = score_issues(
        content=content,
        sentiment=sentiment,
        category=category,
        rating=rating,
    )

    detected: list[dict[str, Any]] = []

    for issue_type, score in scores.items():
        if score >= MIN_ISSUE_SCORE:
            detected.append({
                "issue_type": issue_type,
                "matched_keyword": ", ".join(
                    matched_keywords.get(issue_type, [])
                ),
                "score": score,
            })

    detected.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    if not detected and should_force_issue_from_sentiment(
        sentiment=sentiment,
        rating=rating,
    ):
        fallback_issue_type = infer_fallback_issue_type(text)

        detected.append({
            "issue_type": fallback_issue_type,
            "matched_keyword": "negative_sentiment_fallback",
            "score": FALLBACK_SCORE,
        })

    return detected


# ============================================================
# DELETE ISSUE ANALYSIS
# ============================================================

def delete_issue_analysis(
    db: Session,
    review_id: int,
) -> None:
    """
    Delete old issue analysis for one review.
    """

    db.query(
        IssueAnalysis
    ).filter(
        IssueAnalysis.review_id == review_id
    ).delete(
        synchronize_session=False
    )


# ============================================================
# SAVE ISSUE ANALYSIS
# ============================================================

def save_issue_analysis(
    db: Session,
    review_id: int,
    content: str,
    sentiment: str | None = None,
    category: str | None = "GENERAL",
    rating: int | float | None = None,
) -> list[IssueAnalysis]:
    """
    Save issue analysis for one review.

    Multi-label behavior:
        1. Delete old issues
        2. Detect again
        3. Insert all detected issues
    """

    delete_issue_analysis(
        db=db,
        review_id=review_id,
    )

    detected_issues = detect_issues(
        content=content,
        sentiment=sentiment,
        category=category,
        rating=rating,
    )

    results: list[IssueAnalysis] = []

    for item in detected_issues:
        issue = IssueAnalysis(
            review_id=review_id,
            issue_type=item["issue_type"],
            matched_keyword=item["matched_keyword"],
        )

        db.add(issue)
        results.append(issue)

    db.flush()

    return results


# ============================================================
# GET REVIEW ISSUES
# ============================================================

def get_review_issues(
    db: Session,
    review_id: int,
) -> list[dict[str, Any]]:
    """
    Get all issues of one review.
    """

    issues = (
        db.query(IssueAnalysis)
        .filter(IssueAnalysis.review_id == review_id)
        .all()
    )

    return [
        {
            "id": issue.id,
            "review_id": issue.review_id,
            "issue_type": issue.issue_type,
            "issue_label": ISSUE_LABELS.get(
                issue.issue_type,
                issue.issue_type,
            ),
            "matched_keyword": issue.matched_keyword,
        }
        for issue in issues
    ]


# ============================================================
# GET PRODUCT ISSUE SUMMARY
# ============================================================

def get_product_issue_summary(
    db: Session,
    product_id: int,
) -> dict[str, int]:
    """
    Count issue occurrences by issue type for one product.

    Note:
        Since issue detection is multi-label, total issue occurrences
        can be greater than total reviews with issues.
    """

    rows = (
        db.query(
            IssueAnalysis.issue_type,
            func.count(IssueAnalysis.id),
        )
        .join(
            Review,
            Review.id == IssueAnalysis.review_id,
        )
        .filter(
            Review.product_id == product_id,
        )
        .group_by(
            IssueAnalysis.issue_type,
        )
        .all()
    )

    return {
        issue_type: count
        for issue_type, count in rows
    }


# ============================================================
# GET PRODUCT ISSUE DETAILS
# ============================================================

def get_product_issues(
    db: Session,
    product_id: int,
    page: int = 1,
    page_size: int = 20,
    issue_type: str | None = None,
) -> dict[str, Any] | None:
    """
    Get paginated issue details for one product.

    Because the system is multi-label, one review may appear more than once
    if it has multiple issue types.
    """

    if page < 1:
        page = 1

    if page_size < 1:
        page_size = 20

    if page_size > 100:
        page_size = 100

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        return None

    query = (
        db.query(
            IssueAnalysis,
            Review,
        )
        .join(
            Review,
            Review.id == IssueAnalysis.review_id,
        )
        .filter(
            Review.product_id == product_id,
        )
    )

    if issue_type:
        query = query.filter(
            IssueAnalysis.issue_type == issue_type.upper(),
        )

    total = query.count()

    offset = (page - 1) * page_size

    rows = (
        query
        .order_by(
            Review.review_date.desc(),
            IssueAnalysis.id.asc(),
        )
        .offset(offset)
        .limit(page_size)
        .all()
    )

    issues = []

    for issue, review in rows:
        issues.append({
            "id": issue.id,
            "review_id": issue.review_id,
            "issue_type": issue.issue_type,
            "issue_label": ISSUE_LABELS.get(
                issue.issue_type,
                issue.issue_type,
            ),
            "matched_keyword": issue.matched_keyword,
            "review": {
                "id": review.id,
                "platform_review_id": review.platform_review_id,
                "content": review.content,
                "rating": review.rating,
                "review_date": review.review_date,
            },
        })

    total_pages = (
        (total + page_size - 1) // page_size
        if total
        else 0
    )

    return {
        "product_id": product.id,
        "platform_product_id": product.platform_product_id,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
        "summary": get_product_issue_summary(
            db=db,
            product_id=product_id,
        ),
        "issues": issues,
    }


# ============================================================
# GET TOP PRODUCT ISSUES
# ============================================================

def get_top_product_issues(
    db: Session,
    product_id: int,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Get top issue types of one product.
    """

    if limit < 1:
        limit = 10

    if limit > 100:
        limit = 100

    rows = (
        db.query(
            IssueAnalysis.issue_type,
            func.count(IssueAnalysis.id).label("count"),
        )
        .join(
            Review,
            Review.id == IssueAnalysis.review_id,
        )
        .filter(
            Review.product_id == product_id,
        )
        .group_by(
            IssueAnalysis.issue_type,
        )
        .order_by(
            func.count(IssueAnalysis.id).desc(),
        )
        .limit(limit)
        .all()
    )

    total = sum(
        count
        for _, count in rows
    )

    result = []

    for issue_type, count in rows:
        percentage = (
            round(count / total * 100, 2)
            if total
            else 0
        )

        result.append({
            "issue_type": issue_type,
            "issue_label": ISSUE_LABELS.get(
                issue_type,
                issue_type,
            ),
            "count": count,
            "percentage": percentage,
        })

    return result


# ============================================================
# GET PRODUCT ISSUE STATISTICS
# ============================================================

def get_product_issue_statistics(
    db: Session,
    product_id: int,
) -> dict[str, Any] | None:
    """
    Get issue statistics of one product.
    """

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        return None

    summary = get_product_issue_summary(
        db=db,
        product_id=product_id,
    )

    total_issues = sum(summary.values())

    review_count_with_issues = (
        db.query(
            func.count(func.distinct(IssueAnalysis.review_id))
        )
        .join(
            Review,
            Review.id == IssueAnalysis.review_id,
        )
        .filter(
            Review.product_id == product_id,
        )
        .scalar()
        or 0
    )

    top_issues = get_top_product_issues(
        db=db,
        product_id=product_id,
    )

    return {
        "product_id": product.id,
        "platform_product_id": product.platform_product_id,
        "total_issue_occurrences": total_issues,
        "reviews_with_issues": review_count_with_issues,
        "issue_types": len(summary),
        "summary": summary,
        "top_issues": top_issues,
    }


# ============================================================
# HELPERS FOR PRODUCT CATEGORY
# ============================================================

def get_product_category(product: Product | None) -> str | None:
    """
    Safely get product category from Product model.
    """

    if product is None:
        return None

    for field_name in [
        "category",
        "product_category",
        "category_code",
    ]:
        value = getattr(product, field_name, None)

        if value:
            return str(value)

    return None


# ============================================================
# REANALYZE ONE REVIEW
# ============================================================

def reanalyze_review_issues(
    db: Session,
    review_id: int,
    category: str | None = None,
) -> list[IssueAnalysis] | None:
    """
    Reanalyze issues for one review.
    """

    review = (
        db.query(Review)
        .filter(Review.id == review_id)
        .first()
    )

    if review is None:
        return None

    sentiment = None

    if getattr(review, "analysis", None):
        sentiment = review.analysis.sentiment

    product = (
        db.query(Product)
        .filter(Product.id == review.product_id)
        .first()
    )

    final_category = category or get_product_category(product)

    issues = save_issue_analysis(
        db=db,
        review_id=review.id,
        content=review.content,
        sentiment=sentiment,
        category=final_category,
        rating=review.rating,
    )

    db.commit()

    return issues


# ============================================================
# REANALYZE PRODUCT ISSUES
# ============================================================

def reanalyze_product_issues(
    db: Session,
    product_id: int,
    category: str | None = None,
) -> dict[str, Any] | None:
    """
    Reanalyze issues for all reviews of one product.
    """

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        return None

    final_category = category or get_product_category(product)

    reviews = (
        db.query(Review)
        .filter(Review.product_id == product_id)
        .all()
    )

    analyzed_reviews = 0
    reviews_with_issues = 0
    total_issue_occurrences = 0

    for review in reviews:
        sentiment = None

        if getattr(review, "analysis", None):
            sentiment = review.analysis.sentiment

        issues = save_issue_analysis(
            db=db,
            review_id=review.id,
            content=review.content,
            sentiment=sentiment,
            category=final_category,
            rating=review.rating,
        )

        analyzed_reviews += 1

        if issues:
            reviews_with_issues += 1

        total_issue_occurrences += len(issues)

    db.commit()

    return {
        "product_id": product_id,
        "analyzed_reviews": analyzed_reviews,
        "reviews_with_issues": reviews_with_issues,
        "total_issue_occurrences": total_issue_occurrences,
        "summary": get_product_issue_summary(
            db=db,
            product_id=product_id,
        ),
    }


# ============================================================
# COUNT DETECTED ISSUES
# ============================================================

def count_detected_issues(
    detected_issues: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Count detected issue types from memory.
    """

    counter = Counter()

    for issue in detected_issues:
        issue_type = issue.get("issue_type")

        if issue_type:
            counter[issue_type] += 1

    return dict(counter)