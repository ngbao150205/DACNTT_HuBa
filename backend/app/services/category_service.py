import re


# ============================================================
# CATEGORY KEYWORDS
# ============================================================

CATEGORY_KEYWORDS = {

    "FMCG": [

        "sữa",
        "sữa bột",
        "sữa tươi",
        "thực phẩm",
        "đồ ăn",
        "bánh",
        "kẹo",
        "nước uống",
        "đồ uống",
        "mì",
        "ngũ cốc",
        "cà phê",
        "trà",
        "dầu ăn",
        "gia vị",
        "nước mắm",
        "nước tương",

    ],

    "PHONE": [

        "điện thoại",
        "smartphone",
        "iphone",
        "samsung galaxy",
        "xiaomi",
        "oppo",
        "vivo",
        "realme",
        "pixel",

    ],

    "EARPHONE": [

        "tai nghe",
        "earphone",
        "earbuds",
        "headphone",
        "airpods",
        "bluetooth headset",

    ],

    "CLOTHING": [

        "áo",
        "quần",
        "váy",
        "đầm",
        "hoodie",
        "sweater",
        "cardigan",
        "jacket",
        "áo khoác",
        "jeans",
        "legging",
        "quần short",
        "quần dài",

    ],

    "JEWELRY": [

        "vòng",
        "vòng tay",
        "vòng cổ",
        "dây chuyền",
        "nhẫn",
        "bông tai",
        "hoa tai",
        "khuyên tai",
        "trang sức",
        "bracelet",
        "necklace",
        "ring",
        "earring",

    ],

}


# ============================================================
# NORMALIZE
# ============================================================

def normalize_text(
    text: str
) -> str:

    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# DETECT CATEGORY
# ============================================================

def detect_category(
    text: str
) -> str:

    text = normalize_text(
        text
    )

    if not text:
        return "GENERAL"


    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword in text:

                score += 1

        if score > 0:

            scores[category] = score


    if not scores:

        return "GENERAL"


    return max(
        scores,
        key=scores.get
    )


# ============================================================
# DETECT CATEGORY FROM PRODUCT
# ============================================================

def detect_product_category(
    product_name: str | None,
    product_url: str | None = None
) -> str:

    combined_text = " ".join(
        [
            product_name or "",
            product_url or ""
        ]
    )

    return detect_category(
        combined_text
    )