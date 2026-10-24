"""HTTP replacement for the external API; used only in disposable E2E tests."""
from types import SimpleNamespace
from unittest.mock import patch
import cookie_crawler

partial_requests = 0


def challenge():
    raise ValueError("HTML verification fixture")


def fake_get(session, url, *, headers, params, **kwargs):
    global partial_requests
    assert url == "https://my.lazada.vn/pdp/review/getReviewList"
    assert session.cookies.get("test_cookie") == "synthetic-e2e-cookie"
    assert "Cookie" not in headers
    star, page = params["filter"], params["pageNo"]
    if str(params['itemId']) == '987654322':
        partial_requests += 1
        if partial_requests > 1:
            return SimpleNamespace(status_code=200, headers={}, json=challenge)
        return SimpleNamespace(status_code=200, headers={}, json=lambda: {"model": {
            "items": [{"reviewRelId":f"partial-{index}", "reviewContent":"Hàng giả, yêu cầu hoàn tiền",
                       "rating":1, "buyerName":"Người mua kiểm thử"} for index in range(5)],
            "paging":{"totalPages":2}, "productName":"Sản phẩm bị giới hạn kiểm thử"}})
    content = {1: "Hàng giả lừa đảo, yêu cầu hoàn tiền", 2: "Sản phẩm chất lượng kém, giao hàng chậm",
               3: "Sản phẩm tạm được", 4: "Sản phẩm tốt", 5: "Sản phẩm rất tốt giao hàng nhanh"}[star]
    return SimpleNamespace(status_code=200, headers={}, json=lambda: {"model": {
        "items": [{"reviewRelId":f"url-{star}-{page}", "reviewContent":content,
                   "rating":star, "buyerName":"Người mua kiểm thử", "reviewTime":"2026-10-21"}],
        "paging":{"totalPages":2}, "productName":"Sản phẩm URL kiểm thử"}})

cookie_crawler.curl_requests.Session.get = fake_get
cookie_crawler.time.sleep = lambda seconds: None
import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8002)
