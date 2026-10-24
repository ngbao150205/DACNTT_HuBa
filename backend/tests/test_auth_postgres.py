"""Legacy migration and reset races, in disposable PostgreSQL schemas only."""
import os
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fastapi import HTTPException, Request
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from database.base import Base
from database.auth_migration import migrate_auth_ownership
from database.models import Product, Review, User, AuthSession, PasswordResetToken
from app.api.auth import reset_password
from app.schemas.auth import ResetPasswordRequest
from app.security.auth import token_hash, utcnow
from app.services.auth_service import passwords


@unittest.skipUnless(os.getenv("AUTH_TEST_DATABASE_URL"), "Set AUTH_TEST_DATABASE_URL for isolated PostgreSQL tests")
class AuthPostgresTests(unittest.TestCase):
    def setUp(self):
        self.schema = "auth_migration_test_" + uuid.uuid4().hex
        self.admin = create_engine(os.environ["AUTH_TEST_DATABASE_URL"])
        with self.admin.begin() as c: c.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        url = make_url(os.environ["AUTH_TEST_DATABASE_URL"]).update_query_dict({"options": f"-csearch_path={self.schema}"})
        self.engine = create_engine(url)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()
        with self.admin.begin() as c: c.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        self.admin.dispose()

    def test_legacy_migration_is_idempotent_preserves_rows_and_allows_private_copies(self):
        with Session(self.engine) as db:
            product = Product(platform="lazada", platform_product_id="123", name="Legacy", url="https://www.lazada.vn/products/i123.html")
            db.add(product); db.flush()
            db.add(Review(product_id=product.id, platform="lazada", platform_review_id="r1", content="Dữ liệu cũ")); db.commit()
        with self.engine.begin() as c:
            c.execute(text('ALTER TABLE products DROP COLUMN owner_id'))
            c.execute(text('ALTER TABLE products ADD CONSTRAINT old_product_unique UNIQUE (platform, platform_product_id)'))
            c.execute(text('ALTER TABLE reviews DROP CONSTRAINT uq_review_product_platform_review'))
            c.execute(text('ALTER TABLE reviews ADD CONSTRAINT old_review_unique UNIQUE (platform, platform_review_id)'))
            # create_all sees the old tables, then the migration adds the new column.
            Base.metadata.create_all(c); migrate_auth_ownership(c)
            Base.metadata.create_all(c); migrate_auth_ownership(c)
            self.assertEqual(c.execute(text('SELECT name FROM products')).scalar_one(), "Legacy")
            self.assertEqual(c.execute(text('SELECT content FROM reviews')).scalar_one(), "Dữ liệu cũ")
            self.assertIsNone(c.execute(text('SELECT owner_id FROM products')).scalar_one())
            self.assertIn("uq_product_owner_platform_product", {x["name"] for x in inspect(c).get_unique_constraints("products")})
        with Session(self.engine) as db:
            for email in ["a@example.com", "b@example.com"]:
                user = User(email=email, full_name="Test", password_hash="unused"); db.add(user); db.flush()
                product = Product(owner_id=user.id, platform="lazada", platform_product_id="123", name=email, url="https://www.lazada.vn/products/i123.html")
                db.add(product); db.flush()
                db.add(Review(product_id=product.id, platform="lazada", platform_review_id="r1", content=email))
            db.commit()
            self.assertEqual(db.query(Product).count(), 3); self.assertEqual(db.query(Review).count(), 3)

    def test_two_simultaneous_resets_use_link_once_and_revoke_sessions(self):
        raw = "test-reset-token-that-is-longer-than-thirty-characters"
        with Session(self.engine) as db:
            user = User(email="race@example.com", full_name="Race", password_hash=passwords.hash("old-password-123"))
            db.add(user); db.flush()
            db.add(AuthSession(user_id=user.id, token_hash=token_hash("session"), expires_at=utcnow()+timedelta(days=1)))
            db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash(raw), expires_at=utcnow()+timedelta(minutes=15)))
            db.commit()
        barrier = threading.Barrier(2)
        def reset(index):
            request = Request({"type":"http", "method":"POST", "headers":[], "client": (f"race-{index}", 123)})
            with Session(self.engine) as db:
                barrier.wait(timeout=5)
                try:
                    reset_password(ResetPasswordRequest(token=raw, password=f"new-password-{index}"), request, db)
                    return 200
                except HTTPException as error:
                    db.rollback(); return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool: self.assertEqual(sorted(pool.map(reset, [1,2])), [200,400])
        with Session(self.engine) as db:
            self.assertEqual(db.query(AuthSession).count(), 0)
            self.assertIsNotNone(db.query(PasswordResetToken).one().used_at)

if __name__ == "__main__": unittest.main()
