"""Conservative identity matching across URL, extension and file collection."""

import hashlib
import json
import unicodedata


def fingerprint(content, customer_name, rating):
    def normalize(value):
        return " ".join(unicodedata.normalize("NFC", str(value or "")).split())

    return hashlib.sha256(json.dumps(
        [normalize(content), normalize(customer_name), rating],
        ensure_ascii=False, separators=(",", ":"),
    ).encode()).hexdigest()


def fallback_id(product_id, content, customer_name, rating):
    return f"collected:{product_id}:{fingerprint(content, customer_name, rating)}"


def is_fallback(review_id):
    return str(review_id).startswith("collected:")


class ReviewIdentityConflict(ValueError):
    pass
