"""URL validation and date parsing shared by the active cookie crawler."""
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit


class CrawlUpstreamError(RuntimeError):
    """Lazada did not return a usable review response."""


def parse_product_url(url: str) -> tuple[str, str | None, str]:
    """Accept full VN product URLs; never request an arbitrary user-supplied host."""
    try:
        parsed = urlsplit(url.strip())
        valid = (
            parsed.scheme == "https"
            and parsed.hostname in {"lazada.vn", "www.lazada.vn"}
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
        )
    except (AttributeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("Vui lòng nhập URL sản phẩm đầy đủ https://www.lazada.vn/products/...-i123-s456.html")
    match = re.fullmatch(r"/products/(?:[^/]*-)?i(\d+)(?:-s(\d+))?\.html/?", parsed.path)
    if not match:
        raise ValueError("URL Lazada phải chứa mã sản phẩm dạng -i123.html hoặc -i123-s456.html; hãy mở link rút gọn để lấy URL đầy đủ.")
    product_id, sku_id = match.groups()
    canonical = f"https://www.lazada.vn{parsed.path.rstrip('/')}"
    return product_id, sku_id, canonical


def normalize_review_date(value: Any) -> str | None:
    """Return ISO dates for Vietnamese reviewTime, ISO values or epoch timestamps."""
    if value is None:
        return None
    text = str(value).strip()
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            timestamp = float(text)
            if timestamp >= 1e12:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        vi_date = re.fullmatch(r"(\d{1,2})\s+th(?:g|áng)\s+(\d{1,2})\s+(\d{4})", text, re.I)
        if vi_date:
            day, month, year = map(int, vi_date.groups())
            return datetime(year, month, day).isoformat()
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except (ValueError, OverflowError, OSError):
        return None
