"""ASGI auth, password recovery and tenant isolation; no external network calls."""
import asyncio
import json
import os
import unittest
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.security.auth import COOKIE_NAME, token_hash, utcnow
from app.services import product_service
from database.base import Base
from database.connection import get_db
from database.models import AuthSession, PasswordResetToken, Product, Review, User, UserApiToken

PASSWORD = "mat-khau-test-123"
URL = "https://www.lazada.vn/products/test-i123-s456.html"
AI = {"final": {"sentiment": "Positive", "confidence": .9, "model_name": "underthesea_bilstm_custom_vocab_v3", "method": "model_high_confidence"}}


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.admin_engine = None
        if os.getenv("AUTH_TEST_DATABASE_URL"):
            self.schema = "auth_test_" + uuid.uuid4().hex
            self.admin_engine = create_engine(os.environ["AUTH_TEST_DATABASE_URL"])
            with self.admin_engine.begin() as c: c.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            url = make_url(os.environ["AUTH_TEST_DATABASE_URL"]).update_query_dict({"options": f"-csearch_path={self.schema}"})
            self.engine = create_engine(url)
        else:
            self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        app.dependency_overrides[get_db] = lambda: self.db
        self.mail = patch("app.api.auth.send_reset_email").start()
        self.ai = patch.object(product_service, "predict_sentiment", return_value=AI).start()
        self.env = patch.dict(os.environ, {"AUTH_FRONTEND_URL": "http://localhost:5173", "INGEST_API_KEY": "old-global-key-that-must-not-work-12345"})
        self.env.start()

    def tearDown(self):
        patch.stopall(); self.env.stop(); app.dependency_overrides.clear()
        self.db.close(); self.engine.dispose()
        if self.admin_engine:
            with self.admin_engine.begin() as c: c.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            self.admin_engine.dispose()

    def request(self, path, data=None, *, method=None, cookie=None, key=None, origin=None, extra=()):
        async def run():
            headers = [(b"content-type", b"application/json"), *extra]
            if cookie: headers.append((b"cookie", cookie.encode()))
            if key: headers.append((b"authorization", f"Bearer {key}".encode()))
            if origin: headers.append((b"origin", origin.encode()))
            route, _, query = path.partition("?")
            scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method or ("POST" if data is not None else "GET"),
                     "scheme": "http", "path": route, "raw_path": route.encode(), "query_string": query.encode(),
                     "headers": headers, "server": ("localhost", 8000), "client": ("auth-test", 123)}
            events = []
            async def receive(): return {"type": "http.request", "body": json.dumps(data or {}).encode(), "more_body": False}
            async def send(event): events.append(event)
            await app(scope, receive, send)
            start = next(e for e in events if e["type"] == "http.response.start")
            raw = b"".join(e.get("body", b"") for e in events if e["type"] == "http.response.body")
            return start["status"], json.loads(raw) if raw else None, {k.decode(): v.decode() for k,v in start["headers"]}
        result = asyncio.run(run())
        # Production get_db closes failed requests; the test reuses a session.
        self.db.rollback()
        return result

    def register(self, email="first@example.com"):
        status, data, headers = self.request("/auth/register", {"email": email, "full_name": "Người kiểm thử", "password": PASSWORD})
        self.assertEqual(status, 201, data)
        return headers["set-cookie"].split(";", 1)[0]

    def reset_link(self, email="first@example.com"):
        self.request("/auth/forgot-password", {"email": email})
        link = self.mail.call_args.args[2]
        self.assertEqual(urlsplit(link).netloc, "localhost:5173")
        self.assertEqual(urlsplit(link).query, "")
        return parse_qs(urlsplit(link).fragment)["token"][0]

    def test_register_login_me_logout_and_password_hashing(self):
        cookie = self.register("FIRST@EXAMPLE.COM")
        stored = self.db.query(User).one()
        self.assertEqual(stored.email, "first@example.com")
        self.assertTrue(stored.password_hash.startswith("$argon2id$"))
        self.assertNotEqual(stored.password_hash, PASSWORD)
        self.assertNotEqual(self.db.query(AuthSession).one().token_hash, cookie.split("=", 1)[1])
        self.assertEqual(self.request("/auth/me", cookie=cookie)[1]["user"]["id"], stored.id)
        status, _, headers = self.request("/auth/login", {"email": "first@example.com", "password": PASSWORD})
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", headers["set-cookie"])
        self.assertIn("SameSite=lax", headers["set-cookie"])
        self.assertEqual(self.request("/auth/logout", {}, cookie=cookie)[0], 204)
        self.assertEqual(self.request("/auth/me", cookie=cookie)[0], 401)

    def test_invalid_credentials_validation_and_duplicate_email(self):
        self.register()
        for email, password in [("first@example.com", "wrong"), ("missing@example.com", PASSWORD)]:
            self.assertEqual(self.request("/auth/login", {"email": email, "password": password})[0], 401)
        self.assertEqual(self.request("/auth/register", {"email": "FIRST@EXAMPLE.COM", "full_name": "Other", "password": PASSWORD})[0], 409)
        for values in [{"email": "bad", "full_name": "User", "password": PASSWORD}, {"email": "a@example.com", "full_name": "User", "password": "short"}]:
            self.assertEqual(self.request("/auth/register", values)[0], 422)

    def test_protected_endpoints_and_global_ingest_key_rejected(self):
        for path, body in [("/products", None), ("/products/collection-config", None), ("/products/1/analysis", None), ("/products/1/reviews", None), ("/products/1/histories", None), ("/products/analyze", {"url": URL}), ("/collections/status", None), ("/collections/reviews", {}), ("/collections/import?product_url=x&format=json", {})]:
            self.assertEqual(self.request(path, body)[0], 401, path)
        self.assertEqual(self.request("/collections/status", key=os.environ["INGEST_API_KEY"])[0], 401)

    def test_same_product_and_review_ids_are_private_to_each_user(self):
        cookies = [self.register(), self.register("second@example.com")]
        ids = []
        for index, cookie in enumerate(cookies):
            payload = {"product_url": URL, "product_name": f"Tên riêng {index}", "reviews": [{"review_id": "same-review", "content": f"Bình luận riêng {index}", "rating": 5}]}
            status, data, _ = self.request("/collections/reviews", payload, cookie=cookie)
            self.assertEqual(status, 200, data); ids.append(data["product_db_id"])
        self.assertNotEqual(*ids)
        self.assertEqual(self.db.query(Review).count(), 2)
        self.db.add(Product(platform="lazada", platform_product_id="legacy", name="Legacy", url=URL)); self.db.commit()
        for index, cookie in enumerate(cookies):
            products = self.request("/products", cookie=cookie)[1]["products"]
            self.assertEqual([p["id"] for p in products], [ids[index]])
            for endpoint in ["analysis", "reviews", "histories"]:
                self.assertEqual(self.request(f"/products/{ids[index]}/{endpoint}", cookie=cookie)[0], 200)
                self.assertEqual(self.request(f"/products/{ids[1-index]}/{endpoint}", cookie=cookie)[0], 404)
            own_reviews = self.request(f"/products/{ids[index]}/reviews", cookie=cookie)[1]["reviews"]
            self.assertEqual(own_reviews[0]["content"], f"Bình luận riêng {index}")

    def test_url_analysis_receives_authenticated_owner(self):
        cookie = self.register(); user_id = self.db.query(User).one().id
        with patch("app.api.products.analyze_product", return_value={"ok": True}) as analyze:
            self.assertEqual(self.request("/products/analyze", {"url": URL}, cookie=cookie)[0], 200)
            self.assertEqual(analyze.call_args.kwargs["owner_id"], user_id)

    def test_personal_keys_rotation_expiry_and_account_settings(self):
        cookie = self.register()
        token = self.request("/auth/api-token", {}, cookie=cookie)[1]["token"]
        self.assertEqual(self.request("/collections/status", key=token)[0], 200)
        self.assertEqual(self.request("/auth/api-token", {}, key=token)[0], 401)
        self.assertNotEqual(self.db.query(UserApiToken).one().token_hash, token)
        newer = self.request("/auth/api-token", {}, cookie=cookie)[1]["token"]
        self.assertEqual(self.request("/collections/status", key=token)[0], 401)
        self.assertEqual(self.request("/collections/status", key=newer)[0], 200)
        self.assertEqual(self.request("/auth/api-token", method="DELETE", cookie=cookie)[0], 204)
        self.assertEqual(self.request("/collections/status", key=newer)[0], 401)

    def test_reset_email_generic_response_single_use_and_revocation(self):
        cookie = self.register()
        key = self.request("/auth/api-token", {}, cookie=cookie)[1]["token"]
        expected = self.request("/auth/forgot-password", {"email": "missing@example.com"})
        actual = self.request("/auth/forgot-password", {"email": "first@example.com"})
        self.assertEqual(expected[:2], actual[:2]); self.assertEqual(actual[0], 202)
        token = parse_qs(urlsplit(self.mail.call_args.args[2]).fragment)["token"][0]
        self.assertNotEqual(self.db.query(PasswordResetToken).one().token_hash, token)
        body = {"token": token, "password": "new-password-12345"}
        self.assertEqual(self.request("/auth/reset-password", body)[0], 200)
        self.assertEqual(self.request("/auth/reset-password", body)[0], 400)
        self.assertEqual(self.request("/auth/me", cookie=cookie)[0], 401)
        self.assertEqual(self.request("/collections/status", key=key)[0], 401)
        self.assertEqual(self.request("/auth/login", {"email": "first@example.com", "password": PASSWORD})[0], 401)
        self.assertEqual(self.request("/auth/login", {"email": "first@example.com", "password": body["password"]})[0], 200)

    def test_expired_session_reset_and_replaced_reset_link(self):
        cookie = self.register()
        session = self.db.query(AuthSession).one(); session.expires_at = utcnow() - timedelta(seconds=1); self.db.commit()
        self.assertEqual(self.request("/auth/me", cookie=cookie)[0], 401)
        old = self.reset_link(); new = self.reset_link()
        self.assertEqual(self.request("/auth/reset-password", {"token": old, "password": PASSWORD})[0], 400)
        self.db.query(PasswordResetToken).one().expires_at = utcnow() - timedelta(seconds=1); self.db.commit()
        self.assertEqual(self.request("/auth/reset-password", {"token": new, "password": PASSWORD})[0], 400)

    def test_cross_site_cookie_writes_rejected_and_local_cors_allowed(self):
        cookie = self.register()
        for path, body in [("/auth/logout", {}), ("/auth/forgot-password", {"email": "first@example.com"}), ("/auth/api-token", {}), ("/products/analyze", {"url": URL}), ("/collections/reviews", {})]:
            self.assertEqual(self.request(path, body, cookie=cookie, origin="https://attacker.example")[0], 403, path)
        self.assertEqual(self.request("/auth/logout", {}, cookie=cookie, extra=[(b"sec-fetch-site", b"cross-site")])[0], 403)
        self.assertEqual(self.request("/auth/me", cookie=cookie, origin="http://localhost:5173")[2]["access-control-allow-origin"], "http://localhost:5173")
        self.assertEqual(self.request("/auth/me", cookie=cookie)[0], 200)

    def test_legacy_admin_assignment_preserves_data_and_refuses_collisions(self):
        from scripts.assign_legacy_data import assign_legacy_data
        self.register()
        old = Product(platform="lazada", platform_product_id="legacy", name="Legacy", url=URL)
        self.db.add(old); self.db.commit()
        self.assertEqual(self.request("/products", cookie=self.register("second@example.com"))[1]["products"], [])
        self.assertEqual(assign_legacy_data(self.db, "first@example.com"), 1)
        self.assertEqual(self.db.get(Product, old.id).owner_id, self.db.query(User).filter_by(email="first@example.com").one().id)
        collision = Product(platform="lazada", platform_product_id="legacy", name="Other", url=URL)
        self.db.add(collision); self.db.commit()
        with self.assertRaises(ValueError): assign_legacy_data(self.db, "first@example.com")
        self.db.rollback()
        self.assertIsNone(self.db.get(Product, collision.id).owner_id)

    def test_forgot_password_and_login_rate_limits_survive_failed_requests(self):
        for _ in range(3): self.assertEqual(self.request("/auth/forgot-password", {"email": "missing@example.com"})[0], 202)
        status, _, headers = self.request("/auth/forgot-password", {"email": "missing@example.com"})
        self.assertEqual(status, 429); self.assertGreater(int(headers["retry-after"]), 0)
        for _ in range(10): self.assertEqual(self.request("/auth/login", {"email": "missing@example.com", "password": PASSWORD})[0], 401)
        self.assertEqual(self.request("/auth/login", {"email": "missing@example.com", "password": PASSWORD})[0], 429)

if __name__ == "__main__": unittest.main()
