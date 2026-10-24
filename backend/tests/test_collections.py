"""Hybrid ingestion exercises real ASGI routing/auth and an isolated database."""
import asyncio
import json
import os
import unittest
from datetime import datetime
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from database.base import Base
from database.models import Product, Review, ReviewCollection, AnalysisHistory, User, UserApiToken
from app.security.auth import token_hash, utcnow
from datetime import timedelta
from database.connection import get_db
from app.main import app
from app.services import product_service
from app.services.collection_service import (CollectionValidationError, collect_reviews, normalize_rows,
                                             parse_file, product_identity)
from app.services.ai_client import UnanalyzableReview

KEY = "test-only-key-not-used-in-production-12345"
URL = "https://www.lazada.vn/products/test-i123-s456.html?tracking=removed"
AI = {"final": {"sentiment": "Positive", "confidence": 0.9,
                "model_name": "underthesea_bilstm_custom_vocab_v3", "method": "model_high_confidence"}}
ROW = {"review_id": "r1", "content": "Sản phẩm tốt", "rating": 5, "customer_name": "An"}


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        user = User(email="collections@example.com", full_name="Collection test", password_hash="not-used")
        self.db.add(user); self.db.flush()
        self.owner_id = user.id
        self.db.add(UserApiToken(user_id=user.id, token_hash=token_hash(KEY), expires_at=utcnow() + timedelta(days=1)))
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        self.auth = patch.dict(os.environ, {"INGEST_API_KEY": KEY})
        self.auth.start()
        self.ai = patch.object(product_service, "predict_sentiment", return_value=AI)
        self.predict = self.ai.start()
        self.crawler = patch.object(product_service, "crawl_product", side_effect=AssertionError("Imports must not crawl"))
        self.crawler.start()

    def tearDown(self):
        self.crawler.stop(); self.ai.stop(); self.auth.stop()
        app.dependency_overrides.clear()
        self.db.close(); self.engine.dispose()

    def request(self, path="/collections/reviews", data=None, *, key=KEY, body=None, query="", method="POST"):
        async def run():
            headers = [(b"content-type", b"application/json")]
            if key is not None: headers.append((b"authorization", f"Bearer {key}".encode()))
            scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
                     "scheme": "http", "path": path, "raw_path": path.encode(), "query_string": query.encode(),
                     "headers": headers, "server": ("localhost", 8000), "client": ("test", 123)}
            raw = body if body is not None else json.dumps(data or {}).encode()
            events = []
            async def receive(): return {"type": "http.request", "body": raw, "more_body": False}
            async def send(event): events.append(event)
            await app(scope, receive, send)
            status = next(event["status"] for event in events if event["type"] == "http.response.start")
            payload = b"".join(event.get("body", b"") for event in events if event["type"] == "http.response.body")
            return status, json.loads(payload)
        return asyncio.run(run())

    def collect(self, rows, **kwargs):
        return collect_reviews(self.db, product_url=URL, product_name="Kiểm thử", rows=rows, source="json_import", owner_id=self.owner_id, **kwargs)

    def test_authenticated_route_and_repeat_upload_do_not_recrawl_or_reanalyze(self):
        payload = {"product_url": URL, "reviews": [ROW, ROW, {"content": " "}]}
        for key in [None, "wrong"]:
            status, _ = self.request(data=payload, key=key)
            self.assertEqual(status, 401)
        self.assertEqual(self.db.query(Product).count(), 0)
        for expected_new in [1, 0]:
            status, data = self.request(data=payload)
            self.assertEqual(status, 200, data)
            self.assertEqual(data["collection"]["inserted"], expected_new)
            self.assertEqual(data["collection"]["blank"], 1)
            self.assertEqual(data["collection"]["duplicates_in_batch"], 1)
            self.assertEqual(data["crawl_source"], "api")
            self.assertEqual(data["crawl_status"], "PARTIAL")
        self.assertEqual(self.db.query(Review).count(), 1)
        self.assertEqual(self.db.query(ReviewCollection).count(), 2)
        self.assertEqual(self.predict.call_count, 1)
        self.assertEqual(self.db.query(Review).one().analysis.model_version, "underthesea_bilstm_custom_vocab_v3")

    def test_personal_token_works_without_global_ingest_key(self):
        for configured in ["", "short"]:
            with patch.dict(os.environ, {"INGEST_API_KEY": configured}):
                self.assertEqual(self.request(method="GET", path="/collections/status")[0], 200)
        self.assertEqual(self.request(method="GET", path="/collections/status")[0], 200)

    def test_csv_bom_semicolon_aliases_and_json_metadata(self):
        from urllib.parse import urlencode
        csv = '\ufeffreview_id;content;rating;customer_name;created_at\nr1;"Tốt; giao nhanh";5;An;01/10/2026\n'.encode()
        status, data = self.request("/collections/import", body=csv, query=urlencode({"product_url": URL, "format": "csv"}))
        self.assertEqual(status, 200, data)
        self.assertEqual(self.db.query(Review).one().review_date, datetime(2026, 10, 1))
        payload = {"product_url": URL, "reviews": [{"Review": "Không tốt", "Rating": 1, "Buyer_Name": "Bình"}]}
        status, data = self.request("/collections/import", data=payload, query=urlencode({"product_url": URL, "format": "json"}))
        self.assertEqual(status, 200, data)
        self.assertEqual(data["collection"]["generated_ids"], 1)
        self.assertEqual(self.db.query(Review).count(), 2)

    def test_validation_rejects_entire_batch_before_saving_or_ai(self):
        for bad in [{**ROW, "rating": 6}, {**ROW, "created_at": "yesterday"}, {**ROW, "product_id": "999"},
                    {**ROW, "content": {"html": "bad"}}, {**ROW, "review_id": "collected:fake"},
                    {**ROW, "review_id": True}, {**ROW, "rating": True}]:
            status, data = self.request(data={"product_url": URL, "reviews": [ROW, bad]})
            self.assertEqual(status, 422, data)
        self.assertEqual(self.db.query(Product).count(), 0)
        self.assertEqual(self.predict.call_count, 0)

    def test_invalid_files_product_mismatch_and_size_limit(self):
        from urllib.parse import urlencode
        query = urlencode({"product_url": URL, "format": "json"})
        for raw in [b"not json", b"{}", b"[]", b"\xff", json.dumps({"product_id": "999", "reviews": [ROW]}).encode()]:
            self.assertEqual(self.request("/collections/import", body=raw, query=query)[0], 422)
        self.assertEqual(self.request(body=b"x" * (5 * 1024 * 1024 + 1))[0], 413)
        for raw in [b"content,content\nx,y", b"content,rating\nx,5,extra"]:
            with self.assertRaises(CollectionValidationError): parse_file(raw, "csv")
        with self.assertRaises(CollectionValidationError): normalize_rows([ROW] * 10001, "123")
        self.assertEqual(self.db.query(Product).count(), 0)

    def test_fallback_reconciles_with_real_ids_and_different_real_ids_stay_distinct(self):
        no_id = {k: v for k, v in ROW.items() if k != "review_id"}
        self.collect([no_id])
        original = self.db.query(Review).one().id
        self.assertEqual(self.collect([no_id])["collection"]["inserted"], 0)
        self.assertEqual(self.collect([ROW])["collection"]["inserted"], 0)
        self.assertEqual(self.db.query(Review).one().id, original)
        self.assertEqual(self.db.query(Review).one().platform_review_id, "r1")
        self.collect([{**ROW, "review_id": "r2"}])
        self.assertEqual(self.db.query(Review).count(), 2)
        self.assertEqual(self.predict.call_count, 2)

    def test_url_flow_matches_fallback_created_by_import(self):
        self.collect([{k: v for k, v in ROW.items() if k != "review_id"}])
        payload = {"platform": "lazada", "product_id": "123", "reviews": [ROW]}
        with patch.object(product_service, "crawl_product", return_value=payload):
            result = product_service.analyze_product(self.db, URL, owner_id=self.owner_id)
        self.assertEqual(result["inserted_reviews"], 0)
        self.assertEqual(self.db.query(Review).one().platform_review_id, "r1")

    def test_unnamed_import_preserves_existing_product_name_and_category(self):
        self.collect([ROW])
        product = self.db.query(Product).one()
        product.name = "Điện thoại Samsung"
        self.db.commit()
        result = collect_reviews(self.db, product_url=URL, product_name=None, rows=[ROW], source="extension", owner_id=self.owner_id)
        self.assertEqual(result["product_name"], "Điện thoại Samsung")
        self.assertEqual(result["category"], "PHONE")

    def test_review_id_cannot_be_reused_for_another_product(self):
        self.collect([ROW])
        status, _ = self.request(data={"product_url": URL.replace("i123", "i999"), "reviews": [ROW]})
        self.assertEqual(status, 422)
        self.assertEqual(self.db.query(Product).count(), 1)
        self.assertEqual(self.db.query(ReviewCollection).count(), 1)

    def test_ai_failure_rolls_back_product_reviews_history_and_audit(self):
        self.predict.side_effect = [AI, requests.ConnectionError("AI unavailable")]
        status, _ = self.request(data={"product_url": URL, "reviews": [ROW, {**ROW, "review_id": "r2", "content": "Giao chậm"}]})
        self.assertEqual(status, 502)
        for model in [Product, Review, AnalysisHistory, ReviewCollection]:
            self.assertEqual(self.db.query(model).count(), 0)

    def test_emoji_only_review_is_kept_without_fabricated_sentiment(self):
        self.predict.side_effect = UnanalyzableReview("No text")
        self.collect([{**ROW, "content": "😍"}])
        result = self.collect([{**ROW, "content": "😍"}])
        self.assertEqual(result["collection"]["inserted"], 0)
        self.assertEqual(result["collection"]["duplicates_in_database"], 1)
        self.assertEqual(result["unanalyzable_reviews"], 1)
        self.assertIsNone(self.db.query(Review).one().analysis)

    def test_url_validation_disallows_foreign_hosts_credentials_and_ports(self):
        for url in ["https://evil.example/products/pdp-i123.html", "http://www.lazada.vn/products/pdp-i123.html",
                    "https://x@www.lazada.vn/products/pdp-i123.html", "https://www.lazada.vn:9000/products/pdp-i123.html", None]:
            with self.assertRaises(CollectionValidationError): product_identity(url)
        self.assertEqual(product_identity(URL), ("123", "https://www.lazada.vn/products/pdp-i123.html"))


if __name__ == "__main__": unittest.main()
