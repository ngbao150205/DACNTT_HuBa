"""Dashboard aggregates and historical charts, without crawling or AI calls."""
import json
import os
import unittest
import uuid
from types import SimpleNamespace

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from database.base import Base
from database.dashboard_migration import migrate_dashboard_snapshots
from database.models import AnalysisHistory, Product, Review, ReviewAnalysis, RiskDetection
from app.services.product_analysis_service import get_product_analysis
from app.services.product_service import build_product_analysis, save_analysis_history
from app.services.rating_summary import summarize_ratings


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.product = Product(platform="import", platform_product_id="dashboard-test", name="Test", url="")
        self.db.add(self.product)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_review(self, rating, *, sentiment="Positive", risk=None):
        review = Review(product_id=self.product.id, platform="import", platform_review_id=uuid.uuid4().hex,
                        content="Đánh giá kiểm thử", rating=rating)
        self.db.add(review)
        self.db.flush()
        if sentiment:
            self.db.add(ReviewAnalysis(review_id=review.id, sentiment=sentiment, confidence=0.9))
        if risk:
            self.db.add(RiskDetection(review_id=review.id, risk_flag=risk[0], risk_level=risk[1]))
        self.db.flush()
        return review

    def test_counts_stars_and_excludes_missing_or_invalid_ratings_from_average(self):
        summary = summarize_ratings(SimpleNamespace(rating=star) for star in [1, 2, 3, 4, 5, 5, None, 0, 6])
        self.assertEqual(summary["counts"], {"1": 1, "2": 1, "3": 1, "4": 1, "5": 2})
        self.assertEqual(summary["rated_reviews"], 6)
        self.assertEqual(summary["unrated_reviews"], 3)
        self.assertEqual(summary["average_rating"], 3.33)

    def test_empty_and_unrated_reviews_have_no_fabricated_average(self):
        self.assertIsNone(summarize_ratings([])["average_rating"])
        self.add_review(None, sentiment=None)
        result = get_product_analysis(self.db, self.product.id)["analysis"]
        self.assertIsNone(result["rating_summary"]["average_rating"])
        self.assertEqual(result["rating_summary"]["unrated_reviews"], 1)
        self.assertEqual(result["analyzed_reviews"], 0)
        self.assertEqual(result["risk_summary"], {})

    def test_risk_only_counts_flagged_reviews_including_unknown_level(self):
        for flag, level in [(True, "HIGH"), (True, "MEDIUM"), (True, "LOW"), (False, "LOW"), (True, None)]:
            self.add_review(3, risk=(flag, level))
        self.add_review(5, sentiment=None)
        built = build_product_analysis(self.db, self.product)
        live = get_product_analysis(self.db, self.product.id)["analysis"]
        for result in [built, live]:
            self.assertEqual(result["risk_summary"], {"HIGH": 1, "MEDIUM": 1, "LOW": 1, "UNKNOWN": 1})
            self.assertEqual(result["total_reviews"], 6)
            self.assertEqual(result["analyzed_reviews"], 5)

    def test_old_snapshot_does_not_change_when_more_reviews_are_added(self):
        self.add_review(1, sentiment="Negative", risk=(True, "HIGH"))
        old = save_analysis_history(self.db, self.product, build_product_analysis(self.db, self.product))
        self.add_review(5, risk=(False, "LOW"))
        new = save_analysis_history(self.db, self.product, build_product_analysis(self.db, self.product))
        self.db.commit()
        selected = get_product_analysis(self.db, self.product.id, old.id)
        self.assertEqual(selected["analysis"]["rating_summary"]["counts"]["5"], 0)
        self.assertEqual(selected["analysis"]["rating_summary_source"], "snapshot")
        self.assertEqual(selected["analysis"]["total_reviews"], 1)
        self.assertEqual(selected["analysis"]["risk_summary"], {"HIGH": 1})
        latest = get_product_analysis(self.db, self.product.id)
        self.assertEqual(latest["analysis"]["history_id"], new.id)
        self.assertEqual(latest["analysis"]["rating_summary"]["counts"]["5"], 1)
        self.assertEqual([h["id"] for h in selected["histories"]], [new.id, old.id])

    def test_legacy_history_only_uses_current_ratings_for_latest_with_explicit_source(self):
        self.add_review(5)
        summary = build_product_analysis(self.db, self.product)
        summary.pop("rating_summary")
        old = save_analysis_history(self.db, self.product, summary)
        latest = save_analysis_history(self.db, self.product, summary)
        self.db.commit()
        previous = get_product_analysis(self.db, self.product.id, old.id)["analysis"]
        self.assertIsNone(previous["rating_summary"])
        self.assertEqual(previous["rating_summary_source"], "unavailable")
        current = get_product_analysis(self.db, self.product.id, latest.id)["analysis"]
        self.assertEqual(current["rating_summary"]["counts"]["5"], 1)
        self.assertEqual(current["rating_summary_source"], "current")
        self.assertIsNone(self.db.get(AnalysisHistory, old.id).rating_summary)

    def test_live_aggregation_uses_bounded_queries(self):
        for _ in range(20):
            self.add_review(5, risk=(False, "LOW"))
        self.db.commit()
        self.db.expire_all()
        queries = []
        def record(*args):
            queries.append(args[2])
        event.listen(self.engine, "before_cursor_execute", record)
        try:
            self.assertEqual(get_product_analysis(self.db, self.product.id)["analysis"]["total_reviews"], 20)
            self.assertLessEqual(len(queries), 8)
        finally:
            event.remove(self.engine, "before_cursor_execute", record)


@unittest.skipUnless(os.getenv("AUTH_TEST_DATABASE_URL"), "Set AUTH_TEST_DATABASE_URL for isolated PostgreSQL migration test")
class DashboardPostgresTests(unittest.TestCase):
    def test_upgrade_preserves_legacy_snapshot_and_runs_twice(self):
        admin = create_engine(os.environ["AUTH_TEST_DATABASE_URL"])
        schema = "dashboard_test_" + uuid.uuid4().hex
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = make_url(os.environ["AUTH_TEST_DATABASE_URL"]).update_query_dict({"options": f"-csearch_path={schema}"})
        engine = create_engine(url)
        try:
            Base.metadata.create_all(engine)
            with Session(engine) as db:
                product = Product(platform="import", platform_product_id="legacy", name="Legacy", url="")
                db.add(product); db.flush()
                db.add(AnalysisHistory(product_id=product.id, total_reviews=7, risk_summary=json.dumps({"HIGH": 2})))
                db.commit()
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE analysis_history DROP COLUMN rating_summary"))
                migrate_dashboard_snapshots(connection)
                migrate_dashboard_snapshots(connection)
            with Session(engine) as db:
                snapshot = db.query(AnalysisHistory).one()
                self.assertEqual(snapshot.total_reviews, 7)
                self.assertEqual(json.loads(snapshot.risk_summary), {"HIGH": 2})
                self.assertIsNone(snapshot.rating_summary)
        finally:
            engine.dispose()
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()
