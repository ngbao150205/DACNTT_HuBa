import re
import time
import random

from typing import Any
from urllib.parse import urlparse, parse_qs

from curl_cffi import requests

from fastapi import FastAPI
from pydantic import BaseModel


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Tiki Crawler Service",
    version="1.0.0"
)


class CrawlRequest(BaseModel):
    url: str


# ============================================================
# TIKI CONFIG
# ============================================================

TIKI_BASE_URL = "https://tiki.vn"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0.0.0 "
        "Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://tiki.vn/",
    "Origin": "https://tiki.vn",
}


# ============================================================
# EXTRACT PRODUCT ID
# ============================================================

def extract_product_id(
    url: str
) -> int:
    """
    Extract product_id from Tiki URL.

    Example:
        https://tiki.vn/product-name-p154298071.html

    Return:
        154298071
    """

    match = re.search(
        r"-p(\d+)",
        url
    )

    if not match:
        raise ValueError(
            "Cannot extract product id from URL"
        )

    return int(
        match.group(1)
    )


# ============================================================
# EXTRACT SPID
# ============================================================

def extract_spid(
    url: str
) -> int | None:
    """
    Extract spid from Tiki URL query string.

    Example:
        ?spid=154298080

    Return:
        154298080

    If URL has no spid, return None.
    """

    try:
        parsed_url = urlparse(
            url
        )

        query_params = parse_qs(
            parsed_url.query
        )

        spid_values = query_params.get(
            "spid"
        )

        if not spid_values:
            return None

        return int(
            spid_values[0]
        )

    except Exception:
        return None


# ============================================================
# REQUEST WITH RETRY
# ============================================================

def request_with_retry(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    timeout: int = 30,
    max_retries: int = 3,
    sleep_min: float = 1.0,
    sleep_max: float = 2.5,
):
    """
    Request Tiki API with retry.

    Lý do:
    - Tiki review API đôi khi timeout.
    - Nếu page 2 timeout mà break luôn thì crawler chỉ lấy được page 1.
    """

    last_error = None

    for attempt in range(
        1,
        max_retries + 1
    ):

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                impersonate="chrome",
                timeout=timeout,
            )

            if response.status_code == 200:
                return response

            last_error = Exception(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )

            print(
                "[REQUEST FAILED]",
                f"attempt={attempt}/{max_retries}",
                f"status={response.status_code}",
                f"url={url}",
                f"params={params}",
            )

        except Exception as error:
            last_error = error

            print(
                "[REQUEST ERROR]",
                f"attempt={attempt}/{max_retries}",
                f"url={url}",
                f"params={params}",
                f"error={error}",
            )

        if attempt < max_retries:
            time.sleep(
                random.uniform(
                    sleep_min,
                    sleep_max
                )
            )

    raise last_error


# ============================================================
# CRAWL PRODUCT INFORMATION
# ============================================================

def crawl_tiki_product(
    product_id: int
) -> dict[str, Any]:
    """
    Crawl basic product information from Tiki.

    Current purpose:
    - Get product name
    - Provide data for backend category detection

    Return:
        {
            "product_id": 123,
            "product_name": "..."
        }
    """

    product_url = (
        f"{TIKI_BASE_URL}/api/v2/products/{product_id}"
    )

    try:
        response = request_with_retry(
            url=product_url,
            headers=REQUEST_HEADERS,
            params=None,
            timeout=30,
            max_retries=3,
        )

    except Exception as error:
        print(
            "[PRODUCT REQUEST ERROR]",
            error
        )

        return {
            "product_id": product_id,
            "product_name": None,
        }

    try:
        data = response.json()

    except Exception as error:
        print(
            "[PRODUCT JSON PARSE ERROR]",
            error
        )

        return {
            "product_id": product_id,
            "product_name": None,
        }

    product_name = data.get(
        "name"
    )

    if product_name:
        product_name = str(
            product_name
        ).strip()

    return {
        "product_id": product_id,
        "product_name": product_name,
    }


# ============================================================
# NORMALIZE REVIEW ITEM
# ============================================================

def normalize_review_item(
    item: dict[str, Any],
    product_id: int,
    spid: int | None = None
) -> dict[str, Any] | None:
    """
    Convert raw Tiki review item to internal review format.
    """

    review_id = item.get(
        "id"
    )

    if not review_id:
        return None

    content = item.get(
        "content"
    )

    if not content:
        return None

    content = str(
        content
    ).strip()

    if not content:
        return None

    created_at = (
        item.get("created_at")
        or item.get("created_by")
        or item.get("created")
    )

    return {
        "product_id": product_id,
        "spid": spid,
        "review_id": review_id,
        "content": content,
        "rating": item.get(
            "rating"
        ),
        "created_at": created_at,
    }


# ============================================================
# CRAWL TIKI REVIEWS
# ============================================================

def crawl_tiki_reviews(
    product_id: int,
    spid: int | None = None,
    max_pages: int = 20,
    limit: int = 20
) -> dict[str, Any]:
    """
    Crawl reviews from Tiki.

    Important:
    - product_id comes from -p{id}.html
    - spid comes from query string ?spid=...
    - Some Tiki URLs need spid to get the correct variant reviews.
    """

    reviews: list[dict[str, Any]] = []
    review_ids = set()

    page = 1

    crawl_status = "FULL"
    crawl_error = None
    stopped_at_page = None

    review_api_url = (
        f"{TIKI_BASE_URL}/api/v2/reviews"
    )

    while page <= max_pages:

        params: dict[str, Any] = {
            "product_id": product_id,
            "limit": limit,
            "page": page,
        }

        if spid is not None:
            params["spid"] = spid

        try:
            response = request_with_retry(
                url=review_api_url,
                headers=REQUEST_HEADERS,
                params=params,
                timeout=30,
                max_retries=3,
            )

        except Exception as error:
            crawl_status = "PARTIAL"
            crawl_error = str(
                error
            )
            stopped_at_page = page

            print(
                "[REVIEW REQUEST STOPPED]",
                f"page={page}",
                f"product_id={product_id}",
                f"spid={spid}",
                f"error={error}",
            )

            break

        try:
            data = response.json()

        except Exception as error:
            crawl_status = "PARTIAL"
            crawl_error = (
                f"JSON parse error: {error}"
            )
            stopped_at_page = page

            print(
                "[REVIEW JSON PARSE ERROR]",
                f"page={page}",
                f"error={error}",
            )

            break

        review_list = data.get(
            "data",
            []
        )

        print(
            "[REVIEW PAGE]",
            f"product_id={product_id}",
            f"spid={spid}",
            f"page={page}",
            f"count={len(review_list)}",
        )

        if not review_list:
            break

        added_count = 0

        for item in review_list:

            normalized_review = normalize_review_item(
                item=item,
                product_id=product_id,
                spid=spid,
            )

            if normalized_review is None:
                continue

            review_id = normalized_review[
                "review_id"
            ]

            if review_id in review_ids:
                continue

            review_ids.add(
                review_id
            )

            reviews.append(
                normalized_review
            )

            added_count += 1

        print(
            "[REVIEW PAGE ADDED]",
            f"page={page}",
            f"added={added_count}",
            f"total={len(reviews)}",
        )

        # Nếu page có data nhưng toàn duplicate hoặc không có content,
        # vẫn thử page tiếp theo một vài lần là không cần thiết.
        # Nhưng ở đây cứ đi tiếp để không bỏ sót review.
        page += 1

        time.sleep(
            random.uniform(
                1.0,
                2.5
            )
        )

    return {
        "reviews": reviews,
        "crawl_status": crawl_status,
        "crawl_error": crawl_error,
        "stopped_at_page": stopped_at_page,
        "pages_attempted": page - 1,
        "max_pages": max_pages,
    }


# ============================================================
# CRAWL PRODUCT REVIEWS
# ============================================================

def crawl_product_reviews(
    url: str
) -> dict[str, Any]:
    """
    Main crawler function.

    Input:
        Tiki product URL

    Output:
        {
            "product_id": ...,
            "spid": ...,
            "product_name": ...,
            "total_reviews": ...,
            "crawl_status": "FULL" | "PARTIAL",
            "crawl_error": ...,
            "reviews": [...]
        }
    """

    product_id = extract_product_id(
        url
    )

    spid = extract_spid(
        url
    )

    print(
        "[CRAWL START]",
        f"product_id={product_id}",
        f"spid={spid}",
    )

    product_info = crawl_tiki_product(
        product_id
    )

    product_name = product_info.get(
        "product_name"
    )

    review_result = crawl_tiki_reviews(
        product_id=product_id,
        spid=spid,
        max_pages=20,
        limit=20,
    )

    reviews = review_result.get(
        "reviews",
        []
    )

    result = {
        "product_id": product_id,
        "spid": spid,
        "product_name": product_name,
        "total_reviews": len(reviews),
        "crawl_status": review_result.get(
            "crawl_status"
        ),
        "crawl_error": review_result.get(
            "crawl_error"
        ),
        "stopped_at_page": review_result.get(
            "stopped_at_page"
        ),
        "pages_attempted": review_result.get(
            "pages_attempted"
        ),
        "reviews": reviews,
    }

    print(
        "[CRAWL DONE]",
        f"product_id={product_id}",
        f"spid={spid}",
        f"total_reviews={len(reviews)}",
        f"status={result['crawl_status']}",
    )

    return result


# ============================================================
# API ROUTES
# ============================================================

@app.get("/")
def health_check():
    return {
        "service": "tiki-crawler-service",
        "status": "ok",
    }


@app.post("/crawl")
def crawl(
    request: CrawlRequest
):
    return crawl_product_reviews(
        request.url
    )