from datetime import datetime, timezone
from collections import Counter
import json

from sqlalchemy.orm import Session, selectinload

from database.models import (
    Product,
    Review,
    ReviewAnalysis,
    AnalysisHistory,
)

from app.services.crawler_client import crawl_product
from app.services.ai_client import predict_sentiment, UnanalyzableReview
from app.services.issue_service import save_issue_analysis
from app.services.risk_service import save_risk_detection
from app.services.category_service import detect_product_category
from app.services.review_identity import fingerprint, is_fallback, ReviewIdentityConflict
from app.services.rating_summary import summarize_ratings


# ============================================================
# CONSTANTS
# ============================================================

PLATFORM = "lazada"

MODEL_VERSION = "underthesea_bilstm_custom_vocab_v3"


# ============================================================
# TIMESTAMP
# ============================================================

def convert_timestamp(timestamp):
    """
    Convert ISO review dates or legacy Unix timestamps to UTC datetimes.
    """

    if timestamp is None:
        return None

    try:
        if isinstance(timestamp, str) and not timestamp.strip().replace(".", "", 1).isdigit():
            date = datetime.fromisoformat(timestamp.strip().replace("Z", "+00:00"))
            return date.astimezone(timezone.utc).replace(tzinfo=None) if date.tzinfo else date
        value = float(timestamp)
        if value >= 1e12:
            value /= 1000
        return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None)

    except (TypeError, ValueError, OSError, OverflowError):
        return None


# ============================================================
# FIND PRODUCT
# ============================================================

def get_product(
    db: Session,
    platform_product_id: int,
    *,
    lock: bool = False,
    owner_id: int | None = None,
    platform: str = PLATFORM,
):
    """
    Tìm Product dựa trên:

    - platform
    - platform_product_id
    """

    query = (
        db.query(Product)
        .filter(
            Product.owner_id == owner_id,
            Product.platform == platform,
            Product.platform_product_id
            == str(platform_product_id),
        )
    )
    if lock:
        query = query.with_for_update()
    return query.first()


# ============================================================
# CREATE PRODUCT
# ============================================================

def create_product(
    db: Session,
    product_id: int,
    url: str,
    product_name: str | None = None,
    category: str = "GENERAL",
    owner_id: int | None = None,
    platform: str = PLATFORM,
):
    """
    Tạo Product mới.
    """

    product = Product(
        owner_id=owner_id,
        platform_product_id=str(product_id),
        platform=platform,
        name=(
            product_name
            or f"Lazada Product {product_id}"
        ),
        url=url,
        product_type="my_product",
        category=category,
        total_reviews=0,
        is_active=True,
        last_crawled_at=datetime.utcnow(),
    )

    db.add(product)
    db.flush()

    return product


# ============================================================
# UPDATE PRODUCT
# ============================================================

def update_product(
    product: Product,
    url: str,
    product_name: str | None = None,
    category: str | None = None,
):
    """
    Cập nhật thông tin Product
    sau mỗi lần crawl.
    """

    product.url = url

    if product_name:
        product.name = product_name

    if category:
        product.category = category

    product.last_crawled_at = datetime.utcnow()
    product.updated_at = datetime.utcnow()


# ============================================================
# FIND REVIEW
# ============================================================

def get_review(
    db: Session,
    review_id,
    owner_id: int | None = None,
    platform: str = PLATFORM,
    product_id: int | None = None,
):
    """
    Tìm review dựa trên:

    - platform
    - platform_review_id
    """

    if review_id is None:
        return None

    query = (
        db.query(Review)
        .join(Product, Product.id == Review.product_id)
        .filter(
            Product.owner_id == owner_id,
            Review.platform == platform,
            Review.platform_review_id
            == str(review_id),
        )
    )
    if product_id is not None:
        query = query.filter(Review.product_id == product_id)
    return query.first()


# ============================================================
# CREATE REVIEW
# ============================================================

def create_review(
    db: Session,
    product: Product,
    review_data: dict,
):
    """
    Lưu review mới vào database.
    """

    review_id = review_data.get("review_id")

    if review_id is None:
        raise ValueError(
            "Review does not contain review_id"
        )

    content = review_data.get(
        "content",
        "",
    )

    if not content:
        content = ""

    review = Review(
        product_id=product.id,
        platform_review_id=str(review_id),
        platform=product.platform,
        customer_name=review_data.get(
            "customer_name"
        ),
        content=content,
        rating=review_data.get("rating"),
        review_date=convert_timestamp(
            review_data.get("created_at")
        ),
        is_analyzed=False,
    )

    db.add(review)
    db.flush()

    return review


# ============================================================
# CREATE REVIEW AI ANALYSIS
# ============================================================

def create_review_analysis(
    db: Session,
    review: Review,
    ai_result: dict,
):
    """
    Lưu kết quả Sentiment AI.

    Hàm này chỉ chịu trách nhiệm
    lưu kết quả model vào database.
    """

    if not isinstance(ai_result, dict):
        raise ValueError(
            "AI result must be a dictionary"
        )

    final_result = ai_result.get(
        "final",
        {},
    )

    if not isinstance(final_result, dict):
        raise ValueError(
            "AI result 'final' must be a dictionary"
        )

    sentiment = final_result.get("sentiment")

    if not sentiment:
        raise ValueError(
            "AI result does not contain sentiment"
        )

    confidence = final_result.get(
        "confidence",
        0,
    )

    method = final_result.get("method")

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    analysis = ReviewAnalysis(
        review_id=review.id,
        sentiment=sentiment,
        confidence=confidence,
        model_version=final_result.get("model_name") or MODEL_VERSION,
        analysis_method=method,
    )

    db.add(analysis)
    db.flush()

    return analysis


# ============================================================
# ANALYZE NEW REVIEW
# ============================================================

def analyze_new_review(
    db: Session,
    review: Review,
    category: str = "GENERAL",
):
    """
    Phân tích một review mới.

    Flow:

    Review
       ↓
    Sentiment AI
       ↓
    ReviewAnalysis
       ↓
    Issue Detection
       ↓
    IssueAnalysis
       ↓
    Risk Detection
       ↓
    RiskDetection
       ↓
    is_analyzed = True
    """

    # ========================================================
    # 1. SENTIMENT AI
    # ========================================================

    ai_result = predict_sentiment(
        review.content,
        rating=review.rating
    )

    if not isinstance(ai_result, dict):
        raise ValueError(
            "predict_sentiment() must return a dictionary"
        )

    # ========================================================
    # 2. SAVE SENTIMENT
    # ========================================================

    analysis = create_review_analysis(
        db=db,
        review=review,
        ai_result=ai_result,
    )

    # ========================================================
    # 3. GET FINAL SENTIMENT
    # ========================================================

    final_result = ai_result.get(
        "final",
        {},
    )

    sentiment = final_result.get(
        "sentiment"
    )

    # ========================================================
    # 4. ISSUE ANALYSIS
    # ========================================================

    issue_results = save_issue_analysis(
        db=db,
        review_id=review.id,
        content=review.content,
        sentiment=sentiment,
        category=category,
    )

    # ========================================================
    # 5. RISK DETECTION
    # ========================================================

    risk_result = save_risk_detection(
        db=db,
        review_id=review.id,
        content=review.content,
        sentiment=sentiment,
        rating=review.rating,
    )

    # ========================================================
    # 6. MARK REVIEW AS ANALYZED
    # ========================================================

    review.is_analyzed = True
    review.updated_at = datetime.utcnow()

    db.flush()

    # ========================================================
    # 7. RETURN
    # ========================================================

    return {
        "review": review,
        "ai_result": ai_result,
        "analysis": analysis,
        "issues": issue_results,
        "risk": risk_result,
    }


# ============================================================
# COMPLETE EXISTING REVIEW ANALYSIS
# ============================================================

def complete_existing_review_analysis(
    db: Session,
    review: Review,
    category: str = "GENERAL",
):
    """
    Hoàn thiện dữ liệu phân tích của review cũ.

    Quy tắc:

    - Nếu đã có ReviewAnalysis:
        Không chạy model lại.

    - Nếu chưa có ReviewAnalysis:
        Chạy model để hoàn thiện.

    - Nếu Issue thiếu:
        Bổ sung Issue.

    - Nếu Risk thiếu:
        Bổ sung Risk.
    """

    ai_result = None

    # ========================================================
    # 1. SENTIMENT
    # ========================================================

    if review.analysis:

        sentiment = review.analysis.sentiment

    else:

        ai_result = predict_sentiment(
            review.content,
            rating=review.rating
        )

        if not isinstance(ai_result, dict):
            raise ValueError(
                "predict_sentiment() must return a dictionary"
            )

        create_review_analysis(
            db=db,
            review=review,
            ai_result=ai_result,
        )

        final_result = ai_result.get(
            "final",
            {},
        )

        sentiment = final_result.get(
            "sentiment"
        )

    # ========================================================
    # 2. ISSUE
    # ========================================================

    issue_results = []

    if not review.issue_analysis:

        issue_results = save_issue_analysis(
            db=db,
            review_id=review.id,
            content=review.content,
            sentiment=sentiment,
            category=category,
        )

    # ========================================================
    # 3. RISK
    # ========================================================

    risk_result = review.risk_detection

    if not risk_result:

        risk_result = save_risk_detection(
            db=db,
            review_id=review.id,
            content=review.content,
            sentiment=sentiment,
            rating=review.rating,
        )

    # ========================================================
    # 4. MARK ANALYZED
    # ========================================================

    if review.analysis:

        review.is_analyzed = True
        review.updated_at = datetime.utcnow()

    db.flush()

    return {
        "review": review,
        "ai_result": ai_result,
        "analysis": review.analysis,
        "issues": issue_results,
        "risk": risk_result,
    }


# ============================================================
# BUILD PRODUCT ANALYSIS
# ============================================================

def build_product_analysis(
    db: Session,
    product: Product,
):
    """
    Tổng hợp toàn bộ dữ liệu đã có
    trong database của Product.

    Hàm này KHÔNG gọi AI.

    Data:

    Product
       ↓
    Reviews
       ├── ReviewAnalysis
       ├── IssueAnalysis
       └── RiskDetection
    """

    reviews = (
        db.query(Review)
        .options(selectinload(Review.analysis), selectinload(Review.issue_analysis), selectinload(Review.risk_detection))
        .filter(
            Review.product_id == product.id
        )
        .all()
    )

    # ========================================================
    # COUNTERS
    # ========================================================

    sentiment_counter = Counter()
    issue_counter = Counter()
    risk_counter = Counter()

    analyzed_reviews = 0

    # ========================================================
    # PROCESS REVIEWS
    # ========================================================

    for review in reviews:

        # ====================================================
        # SENTIMENT
        # ====================================================

        if review.analysis:

            sentiment = review.analysis.sentiment

            if sentiment:

                sentiment_counter[sentiment] += 1
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
                risk_counter[risk.risk_level or "UNKNOWN"] += 1

    # ========================================================
    # SENTIMENT COUNTS
    # ========================================================

    positive_count = sentiment_counter.get(
        "Positive",
        0,
    )

    negative_count = sentiment_counter.get(
        "Negative",
        0,
    )

    neutral_count = sentiment_counter.get(
        "Neutral",
        0,
    )

    # ========================================================
    # TOTAL REVIEWS
    # ========================================================

    total_reviews = len(reviews)

    # ========================================================
    # SENTIMENT RATES
    # ========================================================

    positive_rate = (
        round(
            positive_count
            / analyzed_reviews
            * 100,
            2,
        )
        if analyzed_reviews
        else 0
    )

    negative_rate = (
        round(
            negative_count
            / analyzed_reviews
            * 100,
            2,
        )
        if analyzed_reviews
        else 0
    )

    neutral_rate = (
        round(
            neutral_count
            / analyzed_reviews
            * 100,
            2,
        )
        if analyzed_reviews
        else 0
    )

    # ========================================================
    # RESULT
    # ========================================================

    return {
        "total_reviews": total_reviews,
        "analyzed_reviews": analyzed_reviews,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "positive_rate": positive_rate,
        "negative_rate": negative_rate,
        "neutral_rate": neutral_rate,
        "issue_summary": dict(issue_counter),
        "risk_summary": dict(risk_counter),
        "rating_summary": summarize_ratings(reviews),
    }


# ============================================================
# SAVE ANALYSIS HISTORY
# ============================================================

def save_analysis_history(
    db: Session,
    product: Product,
    analysis_result: dict,
):
    """
    Lưu snapshot thống kê của Product.

    History dùng để:

    - xem lịch sử phân tích
    - so sánh sentiment theo thời gian
    - làm biểu đồ trend
    - phục vụ dashboard
    """

    history = AnalysisHistory(
        product_id=product.id,
        total_reviews=analysis_result[
            "total_reviews"
        ],
        analyzed_reviews=analysis_result[
            "analyzed_reviews"
        ],
        positive_count=analysis_result[
            "positive_count"
        ],
        negative_count=analysis_result[
            "negative_count"
        ],
        neutral_count=analysis_result[
            "neutral_count"
        ],
        positive_rate=analysis_result[
            "positive_rate"
        ],
        negative_rate=analysis_result[
            "negative_rate"
        ],
        neutral_rate=analysis_result[
            "neutral_rate"
        ],
        issue_summary=json.dumps(
            analysis_result["issue_summary"],
            ensure_ascii=False,
        ),
        risk_summary=json.dumps(
            analysis_result["risk_summary"],
            ensure_ascii=False,
        ),
        rating_summary=json.dumps(analysis_result["rating_summary"], ensure_ascii=False)
        if analysis_result.get("rating_summary") is not None else None,
        analyzed_at=datetime.utcnow(),
    )

    db.add(history)
    db.flush()

    return history


# ============================================================
# MAIN PRODUCT ANALYSIS
# ============================================================

def analyze_product(
    db: Session,
    url: str,
    owner_id: int | None = None,
):
    return analyze_collected_reviews(db, url, crawl_product(url), owner_id=owner_id)


def analyze_collected_reviews(db: Session, url: str, crawl_result: dict, *, commit=True, owner_id=None, allow_file_import=False):
    """Analyze a collected batch using shared sentiment, issue and risk rules.

    URL crawling and authenticated imports share identity matching and one
    transaction. Import callers also add their audit row before committing.
    """

    try:

        # ====================================================
        # 1. VALIDATE COLLECTED PRODUCT
        # ====================================================

        if not crawl_result:
            raise ValueError(
                "Crawler returned empty result"
            )

        platform = crawl_result.get("platform")
        if platform != PLATFORM and not (allow_file_import and platform == "import"):
            raise ValueError("Crawler phải trả dữ liệu từ Lazada.")

        product_id = crawl_result.get(
            "product_id"
        )

        if product_id is None:
            raise ValueError(
                "Crawler result does not contain product_id"
            )

        crawled_reviews = crawl_result.get(
            "reviews",
            [],
        )

        product_name = crawl_result.get(
            "product_name"
        )
        # Serialize batches for an existing product so different sources cannot
        # create a generated-ID review and its real-ID counterpart concurrently.
        product = get_product(db=db, platform_product_id=product_id, lock=True, owner_id=owner_id, platform=platform)

        # ====================================================
        # 2. DETECT PRODUCT CATEGORY
        # ====================================================

        category = detect_product_category(
            product_name=product_name or (product.name if product else None),
            product_url=url,
        )

        if not category:
            category = "GENERAL"

        # ====================================================
        # 3. FIND OR CREATE PRODUCT
        # ====================================================

        is_new_product = product is None

        if product is None:

            product = create_product(
                db=db,
                product_id=product_id,
                url=url,
                product_name=product_name,
                category=category,
                owner_id=owner_id,
                platform=platform,
            )

        else:

            update_product(
                product=product,
                url=url,
                product_name=product_name,
                category=category,
            )

        # ====================================================
        # 4. PROCESS REVIEWS
        # ====================================================

        new_reviews = []
        processed_existing_reviews = []
        skipped_reviews = []
        unanalyzable_review_ids = []
        failed_reviews = []
        existing_count = 0
        inserted_count = 0

        # Only generated IDs can be reconciled by content. Two distinct real
        # Lazada IDs remain distinct even when their comments are identical.
        identities = {}
        for saved in db.query(Review).filter_by(product_id=product.id, platform=platform):
            key = fingerprint(saved.content, saved.customer_name, saved.rating)
            identities.setdefault(key, []).append(saved)

        for review_data in crawled_reviews:

            review_id = review_data.get(
                "review_id"
            )

            # =================================================
            # REVIEW KHÔNG CÓ ID
            # =================================================

            if review_id is None:
                continue

            # =================================================
            # CHECK REVIEW EXISTING
            # =================================================

            existing_review = get_review(
                db=db,
                review_id=review_id,
                owner_id=owner_id,
                platform=platform,
                product_id=product.id if platform == "import" else None,
            )

            if existing_review and existing_review.product_id != product.id:
                raise ReviewIdentityConflict("ID đánh giá đã thuộc một sản phẩm khác.")

            key = fingerprint(review_data.get("content"), review_data.get("customer_name"), review_data.get("rating"))
            if existing_review is None:
                candidates = identities.get(key, [])
                matching = candidates if is_fallback(review_id) else [r for r in candidates if is_fallback(r.platform_review_id)]
                if matching:
                    existing_review = matching[0]
                    if not is_fallback(review_id):
                        existing_review.platform_review_id = str(review_id)
                        db.flush()

            # =================================================
            # REVIEW CŨ
            # =================================================

            if existing_review:
                existing_count += 1

                # ------------------------------------------------
                # REVIEW ĐÃ HOÀN THIỆN
                # ------------------------------------------------

                if (
                    existing_review.is_analyzed
                    and existing_review.analysis
                    and existing_review.risk_detection
                ):

                    skipped_reviews.append(
                        existing_review
                    )

                    continue

                # ------------------------------------------------
                # REVIEW CŨ CHƯA HOÀN THIỆN
                # ------------------------------------------------

                try:

                    result = (
                        complete_existing_review_analysis(
                            db=db,
                            review=existing_review,
                            category=category,
                        )
                    )

                    processed_existing_reviews.append(
                        result
                    )

                except UnanalyzableReview:
                    # Keep the original review, without assigning a sentiment.
                    unanalyzable_review_ids.append(str(review_id))

                except Exception:

                    failed_reviews.append(
                        {
                            "review_id": str(
                                review_id
                            )
                        }
                    )

                    raise

                continue

            # =================================================
            # REVIEW MỚI
            # =================================================

            try:

                review = create_review(
                    db=db,
                    product=product,
                    review_data=review_data,
                )
                identities.setdefault(key, []).append(review)
                inserted_count += 1

                analysis_result = (
                    analyze_new_review(
                        db=db,
                        review=review,
                        category=category,
                    )
                )

                new_reviews.append(
                    analysis_result
                )

            except UnanalyzableReview:
                # Emoji/punctuation-only reviews must not abort the product.
                unanalyzable_review_ids.append(str(review_id))

            except Exception:

                failed_reviews.append(
                    {
                        "review_id": str(
                            review_id
                        )
                    }
                )

                raise

        # ====================================================
        # 5. UPDATE PRODUCT
        # ====================================================

        product.last_crawled_at = datetime.utcnow()
        product.category = category
        product.updated_at = datetime.utcnow()

        # ====================================================
        # 6. SAVE REVIEWS + ANALYSIS
        # ====================================================

        db.flush()

        # ====================================================
        # 7. BUILD PRODUCT ANALYSIS
        # ====================================================

        analysis = build_product_analysis(
            db=db,
            product=product,
        )

        # ====================================================
        # 8. UPDATE PRODUCT REVIEW COUNT
        # ====================================================

        product.total_reviews = analysis[
            "total_reviews"
        ]

        product.updated_at = datetime.utcnow()

        db.flush()

        # ====================================================
        # 9. SAVE ANALYSIS HISTORY
        # ====================================================

        history = save_analysis_history(
            db=db,
            product=product,
            analysis_result=analysis,
        )

        # ====================================================
        # 10. COMMIT PRODUCT + HISTORY
        # ====================================================

        if commit:
            db.commit()
        else:
            db.flush()

        # ====================================================
        # 11. BUILD RESPONSE REVIEWS
        # ====================================================

        response_reviews = []

        for item in new_reviews:

            review = item["review"]

            ai_result = item["ai_result"]

            issues = item.get(
                "issues",
                [],
            )

            risk = item.get("risk")

            # =================================================
            # ISSUE RESPONSE
            # =================================================

            issue_response = [
                {
                    "issue_type": issue.issue_type,
                    "matched_keyword": issue.matched_keyword,
                }
                for issue in issues
            ]

            # =================================================
            # RISK RESPONSE
            # =================================================

            risk_response = None

            if risk:

                risk_response = {
                    "risk_flag": risk.risk_flag,
                    "risk_level": risk.risk_level,
                    "risk_keyword": risk.risk_keyword,
                }

            # =================================================
            # REVIEW RESPONSE
            # =================================================

            response_reviews.append(
                {
                    "review_id": review.platform_review_id,
                    "content": review.content,
                    "rating": review.rating,
                    "sentiment": ai_result.get(
                        "final"
                    ),
                    "issues": issue_response,
                    "risk": risk_response,
                    "is_analyzed": review.is_analyzed,
                }
            )

        # ====================================================
        # 12. FINAL RESPONSE
        # ====================================================

        return {
            "product_id": product.platform_product_id,
            "platform": product.platform,
            "product_db_id": product.id,
            "product_name": product.name,
            "category": product.category,
            "product_type": product.product_type,
            "is_new_product": is_new_product,
            "existing_reviews": existing_count,
            "inserted_reviews": inserted_count,
            "crawl_status": crawl_result.get("crawl_status"),
            "crawl_source": crawl_result.get("crawl_source"),
            "collection_provider": crawl_result.get("collection_provider", "crawler"),
            "browser_error": crawl_result.get("browser_error"),
            "crawl_error": crawl_result.get("crawl_error"),
            "total_reviews_available": crawl_result.get("total_reviews_available"),
            "pages_attempted": crawl_result.get("pages_attempted"),
            "pages_fetched": crawl_result.get("pages_fetched"),
            "missing_pages": crawl_result.get("missing_pages", []),
            "completed_stars": crawl_result.get("completed_stars", []),
            "incomplete_stars": crawl_result.get("incomplete_stars", []),
            "requires_verification": crawl_result.get("requires_verification", False),
            "resume_from_page": crawl_result.get("resume_from_page"),
            "cached_reviews": crawl_result.get("cached_reviews", 0),
            "newly_fetched_reviews": crawl_result.get("newly_fetched_reviews", len(crawled_reviews)),
            "cache_hit": crawl_result.get("cache_hit", False),
            "cache_reason": crawl_result.get("cache_reason"),
            "retry_after_seconds": crawl_result.get("retry_after_seconds", 0),
            "crawled_reviews": len(
                crawled_reviews
            ),
            "new_reviews": len(
                new_reviews
            ),
            "processed_existing_reviews": len(
                processed_existing_reviews
            ),
            "skipped_reviews": len(
                skipped_reviews
            ),
            "failed_reviews": len(
                failed_reviews
            ),
            "unanalyzable_reviews": len(unanalyzable_review_ids),
            "unanalyzable_review_ids": unanalyzable_review_ids,
            "analysis": analysis,
            "analysis_history_id": history.id,
            "reviews": response_reviews,
        }

    except Exception:

        # ====================================================
        # ROLLBACK
        # ====================================================

        db.rollback()

        raise
