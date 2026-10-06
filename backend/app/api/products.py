from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.schemas.product import (
    AnalyzeProductRequest,
)

from app.database.connection import (
    get_db,
)

from app.database.models import (
    Product,
    Review,
)

from app.services.product_service import (
    analyze_product,
)

from app.services.product_analysis_service import (
    get_product_analysis,
)

from app.services.review_service import (
    get_product_reviews,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# ============================================================
# GET PRODUCTS HISTORY
# ============================================================
# Dùng cho trang Lịch sử phân tích.
# API này lấy danh sách sản phẩm đã lưu trong database.
# Endpoint:
#   GET /products
#   GET /products/
# ============================================================

@router.get("")
@router.get("/")
def get_products_api(
    db: Session = Depends(get_db),
):
    try:
        review_count_subquery = (
            db.query(
                Review.product_id.label("product_id"),
                func.count(Review.id).label("review_count"),
            )
            .group_by(Review.product_id)
            .subquery()
        )

        products = (
            db.query(
                Product.id,
                Product.platform,
                Product.platform_product_id,
                Product.name,
                Product.url,
                Product.seller_name,
                Product.rating,
                Product.total_reviews,
                Product.product_type,
                Product.category,
                Product.is_active,
                Product.created_at,
                Product.updated_at,
                Product.last_crawled_at,
                review_count_subquery.c.review_count,
            )
            .outerjoin(
                review_count_subquery,
                review_count_subquery.c.product_id == Product.id,
            )
            .order_by(Product.created_at.desc())
            .all()
        )

        return {
            "products": [
                {
                    "id": product.id,
                    "platform": product.platform,
                    "platform_product_id": product.platform_product_id,
                    "name": product.name,
                    "url": product.url,
                    "seller_name": product.seller_name,
                    "rating": product.rating,
                    "total_reviews": product.review_count
                    if product.review_count is not None
                    else product.total_reviews,
                    "stored_total_reviews": product.total_reviews,
                    "product_type": product.product_type,
                    "category": product.category,
                    "is_active": product.is_active,
                    "created_at": product.created_at,
                    "updated_at": product.updated_at,
                    "last_crawled_at": product.last_crawled_at,
                }
                for product in products
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ============================================================
# ANALYZE PRODUCT
# ============================================================
# Endpoint:
#   POST /products/analyze
# Body:
#   {
#       "url": "https://tiki.vn/..."
#   }
# ============================================================

@router.post("/analyze")
def analyze_product_endpoint(
    request: AnalyzeProductRequest,
    db: Session = Depends(get_db),
):
    try:
        result = analyze_product(
            db=db,
            url=request.url,
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ============================================================
# GET PRODUCT ANALYSIS
# ============================================================
# Endpoint:
#   GET /products/{product_id}/analysis
# ============================================================

@router.get("/{product_id}/analysis")
def get_product_analysis_api(
    product_id: int,
    db: Session = Depends(get_db),
):
    result = get_product_analysis(
        db=db,
        product_id=product_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return result


# ============================================================
# GET PRODUCT REVIEWS
# ============================================================
# Endpoint:
#   GET /products/{product_id}/reviews?page=1&page_size=10
# ============================================================

@router.get("/{product_id}/reviews")
def get_product_reviews_api(
    product_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    result = get_product_reviews(
        db=db,
        product_id=product_id,
        page=page,
        page_size=page_size,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return result