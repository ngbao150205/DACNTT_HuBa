"""Optional PostgreSQL race test in a unique disposable schema, never user tables."""
import os
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from database.base import Base
from database.models import Product, Review, ReviewCollection
from app.services import product_service
from app.services.collection_service import collect_reviews


@unittest.skipUnless(os.getenv("COLLECTION_TEST_DATABASE_URL"), "Set COLLECTION_TEST_DATABASE_URL for PostgreSQL concurrency test")
class PostgresCollectionTests(unittest.TestCase):
    def test_simultaneous_real_and_generated_ids_are_merged(self):
        engine = create_engine(os.environ["COLLECTION_TEST_DATABASE_URL"])
        schema = "hybrid_test_" + uuid.uuid4().hex
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped_engine = engine.execution_options(schema_translate_map={None: schema})
        try:
            Base.metadata.create_all(scoped_engine)
            with Session(scoped_engine) as db:
                db.add(Product(platform="lazada", platform_product_id="123", name="Test", url="https://www.lazada.vn/products/pdp-i123.html"))
                db.commit()
            barrier = threading.Barrier(2)
            def predict(*args, **kwargs):
                time.sleep(0.2)
                return {"final": {"sentiment": "Positive", "confidence": .9, "model_name": "underthesea_bilstm_custom_vocab_v3"}}
            def collect(real_id):
                row = {"content": "Sản phẩm tốt", "customer_name": "An", "rating": 5}
                if real_id: row["review_id"] = "r1"
                with Session(scoped_engine) as db:
                    barrier.wait(timeout=5)
                    return collect_reviews(db, product_url="https://www.lazada.vn/products/pdp-i123.html",
                                           product_name=None, rows=[row], source="extension")["collection"]["inserted"]
            with patch.object(product_service, "predict_sentiment", side_effect=predict) as ai, ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(collect, [True, False]))
            self.assertEqual(sorted(results), [0, 1])
            self.assertEqual(ai.call_count, 1)
            with Session(scoped_engine) as db:
                self.assertEqual(db.query(Review).count(), 1)
                self.assertEqual(db.query(Review).one().platform_review_id, "r1")
                self.assertEqual(db.query(ReviewCollection).count(), 2)
        finally:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            engine.dispose()


if __name__ == "__main__": unittest.main()
