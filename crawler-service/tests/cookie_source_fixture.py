"""HTTP replacement for the external API; used only in disposable E2E tests."""
from types import SimpleNamespace
from unittest.mock import patch
import cookie_crawler


def fake_get(url, *, headers, params, **kwargs):
    assert url == "https://my.lazada.vn/pdp/review/getReviewList"
    assert headers["Cookie"] == "synthetic-e2e-cookie"
    star, page = params["filter"], params["pageNo"]
    return SimpleNamespace(status_code=200, headers={}, json=lambda: {"model": {
        "items": [{"reviewRelId":f"url-{star}-{page}", "reviewContent":"Sản phẩm rất tốt giao hàng nhanh",
                   "rating":star, "buyerName":"Người mua kiểm thử", "reviewTime":"2026-10-21"}],
        "paging":{"totalPages":2}, "productName":"Sản phẩm URL kiểm thử"}})

cookie_crawler.curl_requests.get = fake_get
cookie_crawler.time.sleep = lambda seconds: None
import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8002)
