from collections import Counter

from sqlalchemy.orm import Session

from app.database.models import (
    Product,
    Review,
    AnalysisHistory,
)


def get_product_analysis(
    db: Session,
    product_id: int
):
    """
    Lấy toàn bộ dữ liệu phân tích Product
    trực tiếp từ PostgreSQL.

    Không crawl.
    Không gọi AI.

    Data source:

        products
            ↓
        reviews
            ↓
        review_analysis
        issue_analysis
        risk_detection
            ↓
        analysis_history
    """

    # ========================================================
    # 1. FIND PRODUCT
    # ========================================================

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id
        )
        .first()
    )

    if product is None:
        return None

    # ========================================================
    # 2. GET REVIEWS
    # ========================================================

    reviews = (
        db.query(Review)
        .filter(
            Review.product_id == product.id
        )
        .all()
    )

    # ========================================================
    # 3. COUNTERS
    # ========================================================

    sentiment_counter = Counter()
    issue_counter = Counter()
    risk_counter = Counter()

    analyzed_reviews = 0

    # ========================================================
    # 4. PROCESS REVIEWS
    # ========================================================

    for review in reviews:

        # ====================================================
        # SENTIMENT
        # ====================================================

        if review.analysis:

            sentiment = (
                review.analysis.sentiment
            )

            if sentiment:

                sentiment_counter[
                    sentiment
                ] += 1

                analyzed_reviews += 1

        # ====================================================
        # ISSUE
        # ====================================================

        for issue in review.issue_analysis:

            if issue.issue_type:

                issue_counter[
                    issue.issue_type
                ] += 1

        # ====================================================
        # RISK
        # ====================================================

        if review.risk_detection:

            risk = review.risk_detection

            if risk.risk_flag:

                if risk.risk_level:

                    risk_counter[
                        risk.risk_level
                    ] += 1

    # ========================================================
    # 5. SENTIMENT COUNTS
    # ========================================================

    positive_count = (
        sentiment_counter.get(
            "Positive",
            0
        )
    )

    negative_count = (
        sentiment_counter.get(
            "Negative",
            0
        )
    )

    neutral_count = (
        sentiment_counter.get(
            "Neutral",
            0
        )
    )

    # ========================================================
    # 6. TOTAL REVIEWS
    # ========================================================

    total_reviews = len(
        reviews
    )

    # ========================================================
    # 7. SENTIMENT RATES
    # ========================================================

    positive_rate = (
        round(
            positive_count
            / analyzed_reviews
            * 100,
            2
        )
        if analyzed_reviews
        else 0
    )

    negative_rate = (
        round(
            negative_count
            / analyzed_reviews
            * 100,
            2
        )
        if analyzed_reviews
        else 0
    )

    neutral_rate = (
        round(
            neutral_count
            / analyzed_reviews
            * 100,
            2
        )
        if analyzed_reviews
        else 0
    )

    # ========================================================
    # 8. GET LATEST ANALYSIS HISTORY
    # ========================================================

    latest_history = (
        db.query(AnalysisHistory)
        .filter(
            AnalysisHistory.product_id
            == product.id
        )
        .order_by(
            AnalysisHistory.analyzed_at.desc()
        )
        .first()
    )

    # ========================================================
    # 9. BUILD HISTORY RESPONSE
    # ========================================================

    history_response = None

    if latest_history:

        history_response = {

            "id":
                latest_history.id,

            "total_reviews":
                latest_history.total_reviews,

            "analyzed_reviews":
                latest_history.analyzed_reviews,

            "positive_count":
                latest_history.positive_count,

            "negative_count":
                latest_history.negative_count,

            "neutral_count":
                latest_history.neutral_count,

            "positive_rate":
                latest_history.positive_rate,

            "negative_rate":
                latest_history.negative_rate,

            "neutral_rate":
                latest_history.neutral_rate,

            "issue_summary":
                latest_history.issue_summary,

            "risk_summary":
                latest_history.risk_summary,

            "analyzed_at":
                latest_history.analyzed_at

        }

    # ========================================================
    # 10. RETURN
    # ========================================================

    return {

        "product": {

            "id":
                product.id,

            "platform_product_id":
                product.platform_product_id,

            "platform":
                product.platform,

            "name":
                product.name,

            "url":
                product.url,

            "seller_name":
                product.seller_name,

            "rating":
                product.rating,

            "product_type":
                product.product_type,

            "category":
                product.category,

            "total_reviews":
                product.total_reviews,

            "is_active":
                product.is_active,

            "created_at":
                product.created_at,

            "updated_at":
                product.updated_at,

            "last_crawled_at":
                product.last_crawled_at

        },

        "analysis": {

            "total_reviews":
                total_reviews,

            "analyzed_reviews":
                analyzed_reviews,

            "positive_count":
                positive_count,

            "negative_count":
                negative_count,

            "neutral_count":
                neutral_count,

            "positive_rate":
                positive_rate,

            "negative_rate":
                negative_rate,

            "neutral_rate":
                neutral_rate,

            "issue_summary":
                dict(
                    issue_counter
                ),

            "risk_summary":
                dict(
                    risk_counter
                )

        },

        "latest_history":
            history_response

    }
