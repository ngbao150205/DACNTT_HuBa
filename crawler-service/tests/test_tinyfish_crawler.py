"""TinyFish contract tests: synthetic SSE only; no paid API or Lazada traffic."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

import tinyfish_crawler as crawler
from lazada_common import CrawlUpstreamError


URL = "https://www.lazada.vn/products/pdp-i123-s456.html"
API_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"
SYNTHETIC_KEY = "synthetic-test-key"


def review(review_id="r1", content="Sản phẩm tốt", rating=5, **extra):
    return {
        "review_id": review_id,
        "content": content,
        "rating": rating,
        "customer_name": "Người mua",
        "created_at": "13 thg 8 2024",
        **extra,
    }


def result(reviews=None, **extra):
    return {
        "product_id": "123",
        "product_name": "Sản phẩm test",
        "source_url": URL,
        "reviews": [review()] if reviews is None else reviews,
        "complete": True,
        "requires_verification": False,
        "pages_fetched": 1,
        "stop_reason": None,
        "total_reviews_available": 1,
        **extra,
    }


def sse_event(payload, event=None):
    lines = [] if event is None else [f"event: {event}"]
    return lines + [f"data: {json.dumps(payload, ensure_ascii=False)}", ""]


def complete(payload=None, **extra):
    return sse_event({
        "type": "COMPLETE", "status": "COMPLETED", "run_id": "synthetic-run",
        "result": result() if payload is None else payload, **extra,
    })


class StreamResponse:
    """The Requests response surface used by the crawler, without any socket."""

    def __init__(self, lines=None, status_code=200, headers=None, failure=None):
        self.status_code = status_code
        self.headers = {"Content-Type": "text/event-stream", **(headers or {})}
        self.lines = complete() if lines is None else lines
        self.failure = failure
        self.closed = False

    def iter_lines(self, decode_unicode=False):
        if not decode_unicode:
            raise AssertionError("SSE must be decoded as text")
        yield from self.lines
        if self.failure is not None:
            raise self.failure

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class TinyFishCrawlerTests(unittest.TestCase):
    def setUp(self):
        self.settings = patch.object(crawler, "crawler_settings", return_value={
            "api_key": SYNTHETIC_KEY, "timeout_seconds": 600,
        }).start()
        self.post = patch.object(crawler.requests, "post").start()
        self.response = StreamResponse()
        self.post.return_value = self.response
        self.addCleanup(patch.stopall)

    def assert_upstream_status(self, expected):
        with self.assertRaises(CrawlUpstreamError) as caught:
            crawler.crawl_product_reviews(URL)
        self.assertEqual(getattr(caught.exception, "status_code", 502), expected)
        self.assertNotIn(SYNTHETIC_KEY, str(caught.exception))
        self.assertEqual(self.post.call_count, 1)
        return caught.exception

    def test_request_uses_fixed_endpoint_canonical_url_and_only_header_auth(self):
        with patch.dict(os.environ, {"LAZADA_COOKIE": "synthetic-private-cookie"}):
            data = crawler.crawl_product_reviews(URL + "?spm=tracking&token=synthetic-secret")
        args, kwargs = self.post.call_args
        self.assertEqual(args, (API_URL,))
        self.assertEqual(kwargs["headers"]["X-API-Key"], SYNTHETIC_KEY)
        self.assertTrue(kwargs["stream"])
        self.assertFalse(kwargs["allow_redirects"])
        self.assertIsInstance(kwargs["timeout"], tuple)
        self.assertEqual(len(kwargs["timeout"]), 2)
        body = kwargs["json"]
        self.assertEqual(body["url"], URL)
        self.assertIsInstance(body["goal"], str)
        self.assertTrue(body["goal"].strip())
        self.assertEqual(body["agent_config"]["max_duration_seconds"], 600)
        self.assertIsInstance(body["output_schema"], dict)
        self.assertNotIn("cookies", kwargs)
        self.assertFalse(any(key.lower() == "cookie" for key in kwargs["headers"]))
        serialized = json.dumps({"body": body, "result": data}, ensure_ascii=False)
        for secret in [SYNTHETIC_KEY, "synthetic-private-cookie", "synthetic-secret"]:
            self.assertNotIn(secret, serialized)
        self.assertEqual(self.post.call_count, 1)
        self.assertTrue(self.response.closed)

    def test_complete_result_maps_to_existing_api_contract(self):
        data = crawler.crawl_product_reviews(URL)
        self.assertEqual(data["product_id"], "123")
        self.assertEqual(data["sku_id"], "456")
        self.assertEqual(data["product_name"], "Sản phẩm test")
        self.assertEqual(data["platform"], "lazada")
        self.assertEqual(data["crawl_source"], "tinyfish")
        self.assertEqual(data["collection_provider"], "tinyfish")
        self.assertEqual(data["crawl_status"], "FULL")
        self.assertEqual(data["newly_fetched_reviews"], 1)
        self.assertEqual(data["cached_reviews"], 0)
        self.assertEqual(data["reviews"][0]["created_at"], "2024-08-13T00:00:00")
        self.assertFalse(data["requires_verification"])

    def test_multiline_sse_ignores_heartbeat_progress_and_supports_json_result(self):
        payload = {"type": "COMPLETE", "status": "COMPLETED", "result": json.dumps(result())}
        pretty = json.dumps(payload, ensure_ascii=False, indent=2)
        lines = [": heartbeat", ""] + sse_event({"type": "PROGRESS", "message": "Working"})
        lines += ["event: COMPLETE"] + ["data: " + line for line in pretty.splitlines()] + [""]
        self.post.return_value = StreamResponse(lines)
        self.assertEqual(crawler.crawl_product_reviews(URL)["crawl_status"], "FULL")

    def test_legacy_result_json_and_run_id_are_supported(self):
        self.post.return_value = StreamResponse(sse_event({
            "type": "COMPLETE", "status": "COMPLETED", "runId": "synthetic-legacy-run",
            "resultJson": json.dumps(result(), ensure_ascii=False),
        }))
        data = crawler.crawl_product_reviews(URL)
        self.assertEqual(data["crawl_status"], "FULL")
        self.assertEqual(len(data["reviews"]), 1)

    def test_more_than_fifty_text_reviews_have_no_artificial_limit(self):
        rows = [review(str(index), f"Nội dung riêng {index}") for index in range(73)]
        self.post.return_value = StreamResponse(complete(result(rows, total_reviews_available=73, pages_fetched=15)))
        data = crawler.crawl_product_reviews(URL)
        self.assertEqual(len(data["reviews"]), 73)
        self.assertEqual(data["newly_fetched_reviews"], 73)
        self.assertEqual(data["pages_fetched"], 15)
        self.assertEqual(data["crawl_status"], "FULL")

    def test_duplicate_ids_removed_and_missing_ids_are_stable(self):
        row = {"content": "  Hàng đẹp  ", "rating": 4, "customer_name": "Khách"}
        rows = [review("r1"), review("r1"), row, dict(row), review("r2")]
        self.post.side_effect = [StreamResponse(complete(result(rows))), StreamResponse(complete(result(rows)))]
        first = crawler.crawl_product_reviews(URL)
        second = crawler.crawl_product_reviews(URL)
        self.assertEqual(len(first["reviews"]), 3)
        self.assertEqual(first["reviews"], second["reviews"])
        generated = next(row for row in first["reviews"] if row["content"] == "Hàng đẹp")
        self.assertTrue(generated["review_id"].startswith("collected:123:"))
        # Two separately identified reviews may legitimately have identical text.
        self.assertEqual({row["review_id"] for row in first["reviews"]} - {generated["review_id"]}, {"r1", "r2"})

    def test_star_only_rows_are_filtered_and_missing_optional_values_are_valid(self):
        rows = [review("blank", "  "), {"content": "Có nhận xét"}]
        self.post.return_value = StreamResponse(complete(result(rows)))
        data = crawler.crawl_product_reviews(URL)
        self.assertEqual(data["crawl_status"], "FULL")
        self.assertEqual(len(data["reviews"]), 1)
        self.assertIsNone(data["reviews"][0]["rating"])

    def test_invalid_rows_preserve_usable_content_but_downgrade_completeness(self):
        for invalid in [
            None, "not a review", {"content": 7}, review("invalid-rating", rating=6),
            review("zero", rating=0), review("boolean", rating=True), review("fraction", rating=2.5),
        ]:
            with self.subTest(invalid=invalid):
                self.post.return_value = StreamResponse(complete(result([review(), invalid])))
                data = crawler.crawl_product_reviews(URL)
                self.assertEqual(data["crawl_status"], "PARTIAL")
                self.assertTrue(any(row["review_id"] == "r1" for row in data["reviews"]))
                self.assertTrue(all(row["rating"] in [None, 1, 2, 3, 4, 5] for row in data["reviews"]))

    def test_unknown_or_false_completion_never_reports_full(self):
        for completion in [False, None, "true", 1]:
            with self.subTest(completion=completion):
                self.post.return_value = StreamResponse(complete(result(complete=completion)))
                data = crawler.crawl_product_reviews(URL)
                self.assertEqual(data["crawl_status"], "PARTIAL")
                self.assertEqual(len(data["reviews"]), 1)
        payload = result()
        payload.pop("complete")
        self.post.return_value = StreamResponse(complete(payload))
        self.assertEqual(crawler.crawl_product_reviews(URL)["crawl_status"], "PARTIAL")

    def test_partial_blocked_result_keeps_collected_reviews(self):
        self.post.return_value = StreamResponse(complete(result(
            complete=False, requires_verification=True, stop_reason="verification_required",
        )))
        data = crawler.crawl_product_reviews(URL)
        self.assertEqual(data["crawl_status"], "PARTIAL")
        self.assertTrue(data["requires_verification"])
        self.assertEqual(len(data["reviews"]), 1)

    def test_blocked_zero_results_is_429(self):
        self.post.return_value = StreamResponse(complete(result(
            [], complete=False, requires_verification=True, stop_reason="verification_required",
        )))
        self.assert_upstream_status(429)

    def test_explicit_empty_complete_result_is_full(self):
        self.post.return_value = StreamResponse(complete(result([], total_reviews_available=0)))
        data = crawler.crawl_product_reviews(URL)
        self.assertEqual(data["crawl_status"], "FULL")
        self.assertEqual(data["reviews"], [])
        self.assertEqual(data["newly_fetched_reviews"], 0)

    def test_wrong_product_or_source_is_never_accepted(self):
        for fields in [
            {"product_id": "124"}, {"product_id": "0123"},
            {"source_url": "https://www.lazada.vn/products/pdp-i999.html"},
            {"source_url": "https://evil.example/products/pdp-i123.html"},
        ]:
            with self.subTest(fields=fields):
                self.post.reset_mock()
                self.post.return_value = StreamResponse(complete(result(**fields)))
                self.assert_upstream_status(502)

    def test_product_identity_suffices_without_optional_source_url(self):
        payload = result()
        payload.pop("source_url")
        self.post.return_value = StreamResponse(complete(payload))
        self.assertEqual(crawler.crawl_product_reviews(URL)["crawl_status"], "FULL")

    def test_malformed_results_are_502(self):
        for payload in [[], "not JSON", {"product_id": "123"}, result(reviews="not a list")]:
            with self.subTest(payload=payload):
                self.post.reset_mock()
                self.post.return_value = StreamResponse(complete(payload))
                self.assert_upstream_status(502)

    def test_malformed_truncated_or_error_stream_is_not_empty_success(self):
        streams = [
            ["data: {not json}", ""],
            sse_event({"type": "PROGRESS", "message": "No final event"}),
            sse_event({"type": "ERROR", "message": SYNTHETIC_KEY + " raw provider detail"}),
            complete(status="FAILED"),
        ]
        for lines in streams:
            with self.subTest(lines=lines):
                self.post.reset_mock()
                self.post.return_value = StreamResponse(lines)
                self.assert_upstream_status(502)

    def test_http_errors_do_not_retry_or_expose_provider_details(self):
        for status, expected in [(401, 503), (403, 503), (402, 503), (429, 429), (500, 502), (302, 502)]:
            with self.subTest(status=status):
                self.post.reset_mock()
                self.post.return_value = StreamResponse(
                    ["data: " + SYNTHETIC_KEY], status_code=status,
                    headers={"Retry-After": "17", "Location": "https://evil.example/"},
                )
                error = self.assert_upstream_status(expected)
                if status == 429:
                    self.assertEqual(getattr(error, "retry_after_seconds", 0), 17)
                self.assertTrue(self.post.return_value.closed)

    def test_request_timeout_and_stream_timeout_are_504_without_retry(self):
        for during_stream in [False, True]:
            with self.subTest(during_stream=during_stream):
                self.post.reset_mock()
                if during_stream:
                    self.post.side_effect = None
                    self.post.return_value = StreamResponse([], failure=requests.Timeout(SYNTHETIC_KEY))
                else:
                    self.post.side_effect = requests.Timeout(SYNTHETIC_KEY)
                self.assert_upstream_status(504)

    def test_transport_failure_is_sanitized_and_not_retried(self):
        self.post.side_effect = requests.ConnectionError(SYNTHETIC_KEY + " raw connection details")
        self.assert_upstream_status(502)

    def test_missing_or_invalid_key_fails_before_network(self):
        for key in ["", "  ", "invalid\nheader", "invalid\rheader"]:
            with self.subTest(key=key):
                self.settings.return_value = {"api_key": key, "timeout_seconds": 600}
                with self.assertRaises(CrawlUpstreamError) as caught:
                    crawler.crawl_product_reviews(URL)
                self.assertEqual(getattr(caught.exception, "status_code", 502), 503)
                self.post.assert_not_called()

    def test_invalid_urls_rejected_before_network(self):
        for url in [
            "https://evil.example/products/pdp-i123.html",
            "https://www.lazada.vn.evil.example/products/pdp-i123.html",
            "https://user:secret@www.lazada.vn/products/pdp-i123.html",
            "http://www.lazada.vn/products/pdp-i123.html",
            "https://www.lazada.vn:444/products/pdp-i123.html",
            "https://s.lazada.vn/s.short",
            "https://www.lazada.vn/catalog/",
            True,
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                crawler.crawl_product_reviews(url)
        self.post.assert_not_called()


class TinyFishSettingsTests(unittest.TestCase):
    def test_mounted_env_is_reloaded_after_atomic_replacement_and_key_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TINYFISH_API_KEY=first-test-key\nTINYFISH_TIMEOUT_SECONDS=120\n")
            with patch.dict(os.environ, {"CRAWLER_ENV_FILE": str(path), "TINYFISH_API_KEY": "stale-process-key"}):
                self.assertEqual(crawler.crawler_settings(), {"api_key": "first-test-key", "timeout_seconds": 120})
                replacement = Path(directory) / "replacement"
                replacement.write_text("TINYFISH_API_KEY=second-test-key\n")
                replacement.replace(path)
                self.assertEqual(crawler.crawler_settings(), {"api_key": "second-test-key", "timeout_seconds": 600})
                path.write_text("TINYFISH_API_KEY=\n")
                self.assertEqual(crawler.crawler_settings()["api_key"], "")

    def test_legacy_env_file_path_is_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TINYFISH_API_KEY=legacy-test-key\n")
            with patch.dict(os.environ, {"LAZADA_ENV_FILE": str(path)}, clear=True):
                self.assertEqual(crawler.crawler_settings()["api_key"], "legacy-test-key")

    def test_crawler_env_path_takes_precedence_over_legacy_path(self):
        with tempfile.TemporaryDirectory() as directory:
            current = Path(directory) / "current.env"
            legacy = Path(directory) / "legacy.env"
            current.write_text("TINYFISH_API_KEY=current-test-key\n")
            legacy.write_text("TINYFISH_API_KEY=legacy-test-key\n")
            with patch.dict(os.environ, {"CRAWLER_ENV_FILE": str(current), "LAZADA_ENV_FILE": str(legacy)}):
                self.assertEqual(crawler.crawler_settings()["api_key"], "current-test-key")


if __name__ == "__main__":
    unittest.main()
