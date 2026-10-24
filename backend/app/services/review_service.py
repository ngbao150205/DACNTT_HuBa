from typing import Optional
from sqlalchemy.orm import Session

from database.models import (
    Product,
    Review
)


def get_product_reviews(
    db: Session,
    product_id: int,
    page: int = 1,
    page_size: int = 10,
    rating: Optional[int] = None
):
    """
    Lấy danh sách review của một product.

    Không crawl.
    Không gọi AI.
    Chỉ đọc dữ liệu từ database.
    """

    # ========================================================
    # 1. VALIDATE PAGINATION
    # ========================================================

    if page < 1:
        page = 1

    if page_size < 1:
        page_size = 10

    if page_size > 100:
        page_size = 100


    # ========================================================
    # 2. FIND PRODUCT
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
    # 3. QUERY REVIEWS
    # ========================================================

    query = (
        db.query(Review)
        .filter(
            Review.product_id == product.id
        )
    )

    if rating is not None:
        query = query.filter(Review.rating == rating)

    query = query.order_by(
        Review.review_date.desc().nullslast(),
        Review.id.desc()
    )

    # ========================================================
    # 4. TOTAL
    # ========================================================

    total_reviews = query.count()


    # ========================================================
    # 5. PAGINATION
    # ========================================================

    offset = (
        page - 1
    ) * page_size


    reviews = (
        query
        .offset(offset)
        .limit(page_size)
        .all()
    )


    # ========================================================
    # 6. BUILD RESPONSE
    # ========================================================

    result = []


    for review in reviews:

        # ----------------------------------------------------
        # SENTIMENT
        # ----------------------------------------------------

        sentiment_data = None


        if review.analysis:

            sentiment_data = {

                "sentiment":
                    review.analysis.sentiment,

                "confidence":
                    review.analysis.confidence,

                "model_version":
                    review.analysis.model_version,

                "method":
                    review.analysis.analysis_method

            }


        # ----------------------------------------------------
        # ISSUE
        # ----------------------------------------------------

        issues = []


        for issue in review.issue_analysis:

            issues.append({

                "issue_type":
                    issue.issue_type,

                "matched_keyword":
                    issue.matched_keyword

            })


        # ----------------------------------------------------
        # RISK
        # ----------------------------------------------------

        risk_data = None


        if review.risk_detection:

            risk_data = {

                "risk_flag":
                    review.risk_detection.risk_flag,

                "risk_level":
                    review.risk_detection.risk_level,

                "risk_keyword":
                    review.risk_detection.risk_keyword

            }


        # ----------------------------------------------------
        # REVIEW
        # ----------------------------------------------------

        result.append({

            "id":
                review.id,

            "review_id":
                review.platform_review_id,

            "content":
                review.content,

            "rating":
                review.rating,

            "review_date":
                review.review_date,

            "sentiment":
                sentiment_data,

            "issues":
                issues,

            "risk":
                risk_data

        })


    # ========================================================
    # 7. PAGINATION INFORMATION
    # ========================================================

    total_pages = (
        (total_reviews + page_size - 1)
        // page_size
        if total_reviews
        else 0
    )


    # ========================================================
    # 8. RETURN
    # ========================================================

    return {

        "product_id":
            product.id,

        "platform_product_id":
            product.platform_product_id,

        "pagination": {

            "page":
                page,

            "page_size":
                page_size,

            "total_reviews":
                total_reviews,

            "total_pages":
                total_pages

        },

        "reviews":
            result

    }
