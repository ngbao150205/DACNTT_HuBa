"""Exercise crawler error handling and platform isolation using in-memory SQLite."""

import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import requests
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.base import Base
from database.models import Product, Review
from app.services import crawler_client, product_service
from app.api.products import analyze_product_endpoint
from app.schemas.product import AnalyzeProductRequest


class LazadaIntegrationTests(unittest.TestCase):
    def test_analysis_pipeline_saves_lazada_and_returns_partial_status(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        payload = {
            "platform": "lazada", "product_id": "3215038850",
            "product_name": "Sản phẩm kiểm thử", "crawl_status": "PARTIAL", "crawl_source": "public_review_page",
            "crawl_error": "Đạt giới hạn trang", "total_reviews_available": 1000,
            "pages_attempted": 1, "pages_fetched": 1, "missing_pages": [2],
            "requires_verification": True, "resume_from_page": 2,
            "browser_error": "Browser blocked",
            "cached_reviews": 1, "newly_fetched_reviews": 0, "cache_hit": True,
            "cache_reason": "verification_cooldown", "retry_after_seconds": 600,
            "reviews": [{"review_id": "456", "content": "Sản phẩm tốt", "rating": 5, "created_at": "2024-08-13T00:00:00"}],
        }
        ai_result = {"final": {"sentiment": "Positive", "confidence": 0.9, "model_name": "underthesea_bilstm_custom_vocab_v3", "method": "model_high_confidence"}}
        with Session(engine) as db, patch.object(product_service, "crawl_product", return_value=payload), patch.object(product_service, "predict_sentiment", return_value=ai_result):
            result = product_service.analyze_product(db, "https://www.lazada.vn/products/i3215038850.html")
            self.assertEqual(result["platform"], "lazada")
            self.assertEqual(result["crawl_status"], "PARTIAL")
            self.assertEqual(result["crawl_source"], "public_review_page")
            self.assertEqual(result["total_reviews_available"], 1000)
            self.assertEqual(result["missing_pages"], [2])
            self.assertTrue(result["requires_verification"])
            self.assertEqual(result["resume_from_page"], 2)
            self.assertEqual(result["browser_error"], "Browser blocked")
            self.assertEqual(result["cached_reviews"], 1)
            self.assertEqual(result["newly_fetched_reviews"], 0)
            self.assertEqual(result["retry_after_seconds"], 600)
            self.assertTrue(result["cache_hit"])
            self.assertEqual(result["new_reviews"], 1)
            self.assertIsNotNone(result["analysis_history_id"])
            saved = db.query(Review).one()
            self.assertEqual(saved.platform, "lazada")
            self.assertEqual(saved.analysis.sentiment, "Positive")
            self.assertEqual(saved.review_date, datetime(2024, 8, 13))
        engine.dispose()

    def test_platform_prevents_collision_with_tiki_data(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            tiki = Product(platform="tiki", platform_product_id="123", name="Tiki cũ", url="https://tiki.vn/p-p123.html")
            db.add(tiki)
            db.flush()
            db.add(Review(product_id=tiki.id, platform="tiki", platform_review_id="456", content="Dữ liệu cũ"))
            db.flush()
            self.assertIsNone(product_service.get_product(db, 123))
            self.assertIsNone(product_service.get_review(db, 456))
            lazada = product_service.create_product(db, 123, "https://www.lazada.vn/products/i123.html")
            lazada_review = product_service.create_review(db, lazada, {"review_id": "456", "content": "Dữ liệu mới", "rating": 5, "created_at": "2024-08-13T00:00:00"})
            db.flush()
            self.assertEqual(lazada.platform, "lazada")
            self.assertEqual(lazada_review.platform, "lazada")
            self.assertEqual(lazada_review.review_date, datetime(2024, 8, 13))
            self.assertEqual(product_service.get_product(db, 123).id, lazada.id)
            self.assertEqual(product_service.get_review(db, 456).id, lazada_review.id)
            self.assertEqual(db.query(Product).filter_by(platform="tiki").count(), 1)
        engine.dispose()

    def test_date_conversion_supports_iso_and_legacy_epochs(self):
        for value in ["2024-08-13T00:00:00", "2024-08-13T07:00:00+07:00", 1723507200, 1723507200000]:
            with self.subTest(value=value):
                self.assertEqual(product_service.convert_timestamp(value), datetime(2024, 8, 13))
        self.assertIsNone(product_service.convert_timestamp("not a date"))

    @patch.object(crawler_client.requests, "post")
    def test_crawler_success_requires_lazada_version(self, post):
        post.return_value = SimpleNamespace(status_code=200, json=lambda: {"product_id": "123"})
        with self.assertRaisesRegex(crawler_client.CrawlerServiceError, "build lại"):
            crawler_client.crawl_product("url")
        post.return_value = SimpleNamespace(status_code=200, json=lambda: {"platform": "lazada", "product_id": "123"})
        self.assertEqual(crawler_client.crawl_product("url")["platform"], "lazada")
        self.assertEqual(post.call_args.kwargs["timeout"], (5, None))

    @patch.object(crawler_client.requests, "post")
    def test_crawler_error_detail_and_status_reach_backend(self, post):
        for status, expected in [(400, 400), (422, 400), (429, 429), (502, 502), (500, 502)]:
            post.return_value = SimpleNamespace(status_code=status, json=lambda: {"detail": "Lazada chặn truy cập"})
            with self.subTest(status=status), self.assertRaises(crawler_client.CrawlerServiceError) as caught:
                crawler_client.crawl_product("url")
            self.assertEqual(caught.exception.status_code, expected)
            self.assertIn("Lazada", str(caught.exception))

    @patch.object(crawler_client.requests, "post")
    def test_timeout_and_connection_failures(self, post):
        for error, status in [(requests.Timeout(), 504), (requests.ConnectionError(), 502)]:
            post.side_effect = error
            with self.assertRaises(crawler_client.CrawlerServiceError) as caught:
                crawler_client.crawl_product("url")
            self.assertEqual(caught.exception.status_code, status)

    def test_backend_endpoint_preserves_crawler_error_status(self):
        with patch("app.api.products.analyze_product", side_effect=crawler_client.CrawlerServiceError("Lazada bị chặn", 502)):
            with self.assertRaises(HTTPException) as caught:
                analyze_product_endpoint(AnalyzeProductRequest(url="url"), db=None, user=SimpleNamespace(id=1))
        self.assertEqual(caught.exception.status_code, 502)
        self.assertEqual(caught.exception.detail, "Lazada bị chặn")


if __name__ == "__main__":
    unittest.main()
