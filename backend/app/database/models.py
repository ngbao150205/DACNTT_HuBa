from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship

from datetime import datetime

from .base import Base


# ==============================
# PRODUCT TABLE
# Lưu thông tin sản phẩm Tiki
# ==============================

class Product(Base):

    __tablename__ = "products"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    name = Column(
        String(255),
        nullable=False
    )


    url = Column(
        String(500),
        unique=True,
        nullable=False
    )


    seller_name = Column(
        String(255)
    )


    rating = Column(
        Float
    )


    total_reviews = Column(
        Integer,
        default=0
    )


    # Shop của mình hay đối thủ
    product_type = Column(
        String(50),
        default="my_product"
    )
    # my_product
    # competitor


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    last_crawled_at = Column(
        DateTime
    )


    reviews = relationship(
        "Review",
        back_populates="product"
    )



# ==============================
# REVIEW TABLE
# Lưu đánh giá khách hàng
# ==============================

class Review(Base):

    __tablename__ = "reviews"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    product_id = Column(
        Integer,
        ForeignKey(
            "products.id"
        ),
        nullable=False
    )


    # ID review trên Tiki
    platform_review_id = Column(
        String(255),
        unique=True
    )


    customer_name = Column(
        String(255)
    )


    content = Column(
        Text,
        nullable=False
    )


    rating = Column(
        Integer
    )


    review_date = Column(
        DateTime
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    product = relationship(
        "Product",
        back_populates="reviews"
    )


    analysis = relationship(
        "ReviewAnalysis",
        back_populates="review",
        uselist=False
    )



# ==============================
# REVIEW ANALYSIS TABLE
# Kết quả từ Model AI
# ==============================

class ReviewAnalysis(Base):

    __tablename__ = "review_analysis"


    id = Column(
        Integer,
        primary_key=True
    )


    review_id = Column(
        Integer,
        ForeignKey(
            "reviews.id"
        )
    )


    # Positive / Negative / Neutral
    sentiment = Column(
        String(50)
    )


    # Độ tin cậy model
    confidence = Column(
        Float
    )


    # Model version
    model_version = Column(
        String(100)
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    review = relationship(
        "Review",
        back_populates="analysis"
    )


# ==============================
# ISSUE ANALYSIS TABLE
# Rule-based phân loại nguyên nhân
# ==============================

class IssueAnalysis(Base):

    __tablename__ = "issue_analysis"


    id = Column(
        Integer,
        primary_key=True
    )


    review_id = Column(
        Integer,
        ForeignKey(
            "reviews.id"
        )
    )


    issue_type = Column(
        String(100)
    )

    """
    Các loại:

    PRODUCT_QUALITY
    PACKAGING
    SHIPPING
    CUSTOMER_SERVICE

    """


    matched_keyword = Column(
        String(255)
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )



# ==============================
# RISK DETECTION TABLE
# Cảnh báo review nguy hiểm
# ==============================

class RiskDetection(Base):

    __tablename__ = "risk_detection"


    id = Column(
        Integer,
        primary_key=True
    )


    review_id = Column(
        Integer,
        ForeignKey(
            "reviews.id"
        )
    )


    risk_flag = Column(
        Boolean,
        default=False
    )


    risk_level = Column(
        String(50)
    )

    """
    LOW
    MEDIUM
    HIGH
    """


    risk_keyword = Column(
        String(255)
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )



# ==============================
# ANALYSIS HISTORY TABLE
# Lưu lịch sử mỗi lần phân tích
# ==============================

class AnalysisHistory(Base):

    __tablename__ = "analysis_history"


    id = Column(
        Integer,
        primary_key=True
    )


    product_id = Column(
        Integer,
        ForeignKey(
            "products.id"
        )
    )


    total_reviews = Column(
        Integer
    )


    positive_count = Column(
        Integer
    )


    negative_count = Column(
        Integer
    )


    neutral_count = Column(
        Integer
    )


    analyzed_at = Column(
        DateTime,
        default=datetime.utcnow
    )