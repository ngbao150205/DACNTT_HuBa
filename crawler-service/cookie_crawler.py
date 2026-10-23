"""The supplied star-filter crawler, adapted to the app response contract."""
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import re
import tempfile
import time
import unicodedata

import pandas as pd
from curl_cffi import requests as curl_requests
from curl_cffi.requests.cookies import Cookies
from dotenv import dotenv_values
from lazada_common import CrawlUpstreamError, parse_product_url, normalize_review_date

logger = logging.getLogger(__name__)


def crawler_settings():
    """Read mounted .env for each crawl; never log or return cookie contents."""
    path = Path(os.getenv("LAZADA_ENV_FILE", "/run/duancntt/crawler.env"))
    config = dotenv_values(path, interpolate=False) if path.is_file() else os.environ
    return {"cookie": (config.get("LAZADA_COOKIE") or "").strip(),
            "user_agent": (config.get("LAZADA_USER_AGENT") or "").strip() or None}


def cookie_jar_from_header(cookie):
    """Validate a Cookie header value and seed a private, domain-scoped jar."""
    jar = Cookies()
    if not cookie:
        return jar
    if re.match(r"(?i)^cookie\s*:", cookie) or re.search(r"[\x00-\x1f\x7f]", cookie):
        raise ValueError("LAZADA_COOKIE phải là giá trị header Cookie trên một dòng, không kèm chữ Cookie:.")
    for part in cookie.split(";"):
        if not part.strip():
            continue
        name, separator, value = part.strip().partition("=")
        if not separator or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
            raise ValueError("LAZADA_COOKIE cần có dạng ten=gia_tri; ten_khac=gia_tri_khac, không phải lệnh curl.")
        jar.set(name, value, domain=".lazada.vn", path="/", secure=True)
    return jar


def _fallback_id(product_id, content, name, rating):
    def normalize(value):
        return " ".join(unicodedata.normalize("NFC", str(value or "")).split())
    digest = hashlib.sha256(json.dumps([normalize(content), normalize(name), rating],
                            ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return f"collected:{product_id}:{digest}"


def crawl_lazada_reviews(product_id: int, datapath: str, stars: tuple = (1, 2, 3, 4, 5),
                         max_pages: int | None = None, cookie: str | None = None, *, user_agent=None):
    """Return content-only reviews and completeness metadata in DataFrame.attrs.

    Same function interface as the supplied implementation. Defaults cover all
    five ratings. Stop on access challenges rather than continuing other filters.
    """
    if isinstance(product_id, str) and not product_id.strip().isdigit():
        product_id = parse_product_url(product_id)[0]
    if isinstance(product_id, bool) or not str(product_id).isdigit():
        raise ValueError("ID sản phẩm không hợp lệ.")
    product_id = str(int(product_id))
    if max_pages is not None and (isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1):
        raise ValueError("max_pages phải là số nguyên >= 1 hoặc None.")
    if any(isinstance(star, bool) or str(star) not in {"1", "2", "3", "4", "5"} for star in stars):
        raise ValueError("stars chỉ nhận các giá trị từ 1 đến 5.")
    stars = tuple(sorted({int(star) for star in stars}))
    if not stars: raise ValueError("stars không được để trống.")
    headers = {"Accept": "application/json, text/plain, */*",
               "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
               "Referer": f"https://www.lazada.vn/products/pdp-i{product_id}.html"}
    if user_agent:
        headers["User-Agent"] = user_agent
    cookie_jar = cookie_jar_from_header(cookie)
    reviews, seen, completed_stars = [], set(), []
    pages_attempted = pages_crawled = 0
    failure = None
    retry_after = 0
    requires_verification = False
    product_name = None
    with curl_requests.Session(cookies=cookie_jar) as session:
        for index, star in enumerate(stars):
            if index: time.sleep(random.uniform(10, 20))
            page = 1
            signatures = set()
            while max_pages is None or page <= max_pages:
                pages_attempted += 1
                try:
                    response = session.get("https://my.lazada.vn/pdp/review/getReviewList", headers=headers,
                        params={"itemId": product_id, "pageSize": 5, "filter": star, "sort": 0, "pageNo": page},
                        impersonate="chrome", timeout=15, allow_redirects=False)
                    if response.status_code != 200:
                        requires_verification = response.status_code in {401, 403, 429}
                        try: retry_after = max(0, int(response.headers.get("Retry-After", 0)))
                        except (ValueError, TypeError): pass
                        failure = f"Lazada trả HTTP {response.status_code}; đã dừng tại {star} sao, trang {page}."
                        break
                    try:
                        payload = response.json()
                    except ValueError:
                        requires_verification = True
                        failure = f"Lazada trả trang xác minh thay vì JSON tại {star} sao, trang {page}."
                        break
                    if not isinstance(payload, dict): raise ValueError()
                    model = payload.get("model") or {}
                    if not isinstance(model, dict): raise ValueError()
                    data = model.get("items")
                    if data is None:
                        data = ((payload.get("data") or {}).get("module") or {}).get("reviews")
                    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
                        requires_verification = True
                        failure = f"Lazada chưa cung cấp danh sách review hợp lệ tại {star} sao, trang {page}."
                        break
                    pages_crawled += 1
                    if not data:
                        completed_stars.append(star)
                        break
                    signature = hashlib.sha256(json.dumps([
                        [row.get("reviewRelId") or row.get("reviewRateId") or row.get("reviewId"),
                         row.get("reviewContent"), row.get("buyerName"), row.get("rating"), row.get("reviewTime")]
                        for row in data], ensure_ascii=False).encode()).hexdigest()
                    if signature in signatures:
                        failure = f"Lazada lặp lại trang review tại {star} sao, trang {page}; chưa xác nhận đã lấy đủ."
                        break
                    signatures.add(signature)
                    name = model.get("productName") or (model.get("item") or {}).get("itemTitle")
                    if isinstance(name, str) and name.strip(): product_name = name.strip()[:500]
                    new_count = 0
                    for review in data:
                        content = review.get("reviewContent")
                        if not isinstance(content, str) or not content.strip(): continue
                        rating = review.get("rating")
                        if isinstance(rating, bool): continue
                        try: rating = int(rating)
                        except (ValueError, TypeError): continue
                        if rating != star: continue
                        content = content.strip()
                        customer = review.get("buyerName")
                        if not isinstance(customer, str): customer = None
                        review_id = review.get("reviewRelId") or review.get("reviewRateId") or review.get("reviewId")
                        review_id = str(review_id) if review_id is not None else _fallback_id(product_id, content, customer, rating)
                        if review_id in seen: continue
                        seen.add(review_id); new_count += 1
                        reviews.append({"review_id": review_id, "rating": rating, "title": review.get("reviewTitle"),
                            "content": content, "thank_count": review.get("likeCount"),
                            "created_at": normalize_review_date(review.get("reviewTime") or review.get("boughtDate")), "customer_name": customer})
                    logger.info("Lazada product=%s stars=%s page=%s new_reviews=%s", product_id, star, page, new_count)
                    total_pages = (model.get("paging") or {}).get("totalPages")
                    if total_pages is not None and int(total_pages) > 0 and page >= int(total_pages):
                        completed_stars.append(star)
                        break
                except Exception:
                    failure = f"Không đọc được review Lazada tại {star} sao, trang {page}; đã giữ dữ liệu lấy được."
                    break
                page += 1
                if max_pages is not None and page > max_pages:
                    failure = f"Đã đạt max_pages={max_pages} tại mức {star} sao; chưa xác nhận đã lấy đủ."
                    break
                time.sleep(random.uniform(1.5, 3.5))
            if failure: break
    frame = pd.DataFrame(reviews, columns=["review_id", "rating", "title", "content", "thank_count", "created_at", "customer_name"])
    frame.attrs["crawl"] = {"product_id": product_id, "product_name": product_name,
        "crawl_status": "FULL" if len(completed_stars) == len(stars) else "PARTIAL", "crawl_error": failure,
        "pages_attempted": pages_attempted, "pages_fetched": pages_crawled,
        "completed_stars": completed_stars, "incomplete_stars": [star for star in stars if star not in completed_stars],
        "stopped_at_star": star if failure else None, "stopped_at_page": page if failure else None,
        "requires_verification": requires_verification, "retry_after_seconds": retry_after}
    if failure:
        logger.warning("Lazada crawl partial product=%s reviews=%s stopped_star=%s stopped_page=%s requires_verification=%s: %s",
                       product_id, len(reviews), star, page, requires_verification, failure)
    if not frame.empty and datapath:
        directory = Path(datapath); directory.mkdir(parents=True, exist_ok=True)
        # Atomic replacement keeps simultaneous same-product exports valid.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, suffix=".csv", delete=False) as stream:
                temporary = stream.name
            frame.to_csv(temporary, index=False, encoding="utf-8-sig")
            os.replace(temporary, directory / f"{product_id}_1.csv")
        finally:
            if temporary and Path(temporary).exists(): Path(temporary).unlink()
    return frame


def crawl_product_reviews(url):
    product_id, sku_id, _ = parse_product_url(url)
    settings = crawler_settings()
    if not settings["cookie"]:
        error = CrawlUpstreamError("Chưa cấu hình LAZADA_COOKIE trong .env. Cập nhật cookie rồi phân tích lại URL.")
        error.status_code = 503
        raise error
    frame = crawl_lazada_reviews(product_id, os.getenv("LAZADA_EXPORT_DIR", "/var/lib/crawler/exports"),
                                stars=(1, 2, 3, 4, 5), max_pages=None, **settings)
    metadata = frame.attrs["crawl"]
    if frame.empty and metadata["crawl_status"] == "PARTIAL":
        error = CrawlUpstreamError(metadata["crawl_error"] or "Chưa lấy được đánh giá Lazada.")
        error.status_code = 429 if metadata["requires_verification"] else 502
        error.retry_after_seconds = metadata["retry_after_seconds"]
        raise error
    return {**metadata, "platform": "lazada", "sku_id": sku_id, "crawl_source": "cookie_star_filter",
            "reviews": frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records"), "newly_fetched_reviews": len(frame), "cached_reviews": 0}
