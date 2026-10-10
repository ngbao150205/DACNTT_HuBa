from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)

from sqlalchemy.orm import relationship

from .base import Base


# ============================================================
# PRODUCT
# ============================================================

class Product(Base):

    __tablename__ = "products"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # PLATFORM
    # ========================================================

    platform = Column(
        String(50),
        nullable=False,
        default="tiki",
        index=True,
    )

    # ========================================================
    # TIKI PRODUCT ID
    # ========================================================

    platform_product_id = Column(
        String(255),
        nullable=False,
    )

    # ========================================================
    # PRODUCT INFORMATION
    # ========================================================

    name = Column(
        String(500),
        nullable=False,
    )

    url = Column(
        String(1000),
        nullable=False,
    )

    seller_name = Column(
        String(255),
        nullable=True,
    )

    rating = Column(
        Float,
        nullable=True,
    )

    total_reviews = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # ========================================================
    # PRODUCT TYPE
    # ========================================================

    product_type = Column(
        String(50),
        nullable=False,
        default="my_product",
        index=True,
    )

    """
    Các giá trị:

    my_product
        Sản phẩm của shop đang quản lý.

    competitor
        Sản phẩm của đối thủ.
    """

    # ========================================================
    # PRODUCT CATEGORY
    # ========================================================

    category = Column(
        String(100),
        nullable=False,
        default="GENERAL",
        index=True,
    )

    """
    Ví dụ:

    GENERAL
    COSMETICS
    FOOD
    ELECTRONICS
    FASHION
    HOME
    HEALTH
    ...
    """

    # ========================================================
    # STATUS
    # ========================================================

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    last_crawled_at = Column(
        DateTime,
        nullable=True,
    )

    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    reviews = relationship(
        "Review",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    analysis_history = relationship(
        "AnalysisHistory",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="AnalysisHistory.analyzed_at.desc()",
    )

    # ========================================================
    # CONSTRAINTS / INDEXES
    # ========================================================

    __table_args__ = (

        # Một sản phẩm Tiki chỉ xuất hiện một lần
        UniqueConstraint(
            "platform",
            "platform_product_id",
            name="uq_product_platform_product",
        ),

        # Tìm sản phẩm theo platform + product ID
        Index(
            "ix_products_platform_product_id",
            "platform",
            "platform_product_id",
        ),

    )


# ============================================================
# REVIEW
# ============================================================

class Review(Base):

    __tablename__ = "reviews"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # PRODUCT
    # ========================================================

    product_id = Column(
        Integer,
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # PLATFORM
    # ========================================================

    platform = Column(
        String(50),
        nullable=False,
        default="tiki",
        index=True,
    )

    # ========================================================
    # TIKI REVIEW ID
    # ========================================================

    platform_review_id = Column(
        String(255),
        nullable=False,
    )

    # ========================================================
    # CUSTOMER
    # ========================================================

    customer_name = Column(
        String(255),
        nullable=True,
    )

    # ========================================================
    # REVIEW CONTENT
    # ========================================================

    content = Column(
        Text,
        nullable=False,
    )

    rating = Column(
        Integer,
        nullable=True,
    )

    review_date = Column(
        DateTime,
        nullable=True,
    )

    # ========================================================
    # ANALYSIS STATUS
    # ========================================================

    is_analyzed = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    """
    False
        Review chưa được model xử lý.

    True
        Review đã hoàn tất pipeline:

        Sentiment Model
            ↓
        Issue Rule-based
            ↓
        Risk Detection
    """

    # ========================================================
    # TIMESTAMP
    # ========================================================

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    product = relationship(
        "Product",
        back_populates="reviews",
    )

    analysis = relationship(
        "ReviewAnalysis",
        back_populates="review",
        uselist=False,
        cascade="all, delete-orphan",
    )

    issue_analysis = relationship(
        "IssueAnalysis",
        back_populates="review",
        cascade="all, delete-orphan",
    )

    risk_detection = relationship(
        "RiskDetection",
        back_populates="review",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ========================================================
    # CONSTRAINTS / INDEXES
    # ========================================================

    __table_args__ = (

        # Một review Tiki chỉ xuất hiện một lần
        UniqueConstraint(
            "platform",
            "platform_review_id",
            name="uq_review_platform_review",
        ),

        # Tối ưu tìm review theo product
        Index(
            "ix_reviews_product_date",
            "product_id",
            "review_date",
        ),

        # Tối ưu tìm review theo platform + review ID
        Index(
            "ix_reviews_platform_review_id",
            "platform",
            "platform_review_id",
        ),

    )


# ============================================================
# REVIEW ANALYSIS
# ============================================================

class ReviewAnalysis(Base):

    __tablename__ = "review_analysis"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # REVIEW
    # ========================================================

    review_id = Column(
        Integer,
        ForeignKey(
            "reviews.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )

    # ========================================================
    # SENTIMENT
    # ========================================================

    sentiment = Column(
        String(50),
        nullable=False,
        index=True,
    )

    """
    Giá trị:

    Positive
    Negative
    Neutral
    """

    # ========================================================
    # CONFIDENCE
    # ========================================================

    confidence = Column(
        Float,
        nullable=True,
    )

    # ========================================================
    # MODEL INFORMATION
    # ========================================================

    model_version = Column(
        String(100),
        nullable=True,
    )

    analysis_method = Column(
        String(100),
        nullable=True,
    )

    """
    Ví dụ:

    model_agreement
    fasttext_higher_confidence
    keras_higher_confidence
    ensemble
    """

    # ========================================================
    # TIMESTAMP
    # ========================================================

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # ========================================================
    # RELATIONSHIP
    # ========================================================

    review = relationship(
        "Review",
        back_populates="analysis",
    )


# ============================================================
# ISSUE ANALYSIS
# ============================================================

class IssueAnalysis(Base):

    __tablename__ = "issue_analysis"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # REVIEW
    # ========================================================

    review_id = Column(
        Integer,
        ForeignKey(
            "reviews.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # ISSUE TYPE
    # ========================================================

    issue_type = Column(
        String(100),
        nullable=False,
        index=True,
    )

    """
    Các loại:

    PRODUCT_QUALITY
    PACKAGING
    SHIPPING
    CUSTOMER_SERVICE
    PRICE
    OTHER
    """

    # ========================================================
    # MATCHED KEYWORD
    # ========================================================

    matched_keyword = Column(
        String(255),
        nullable=True,
    )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # ========================================================
    # RELATIONSHIP
    # ========================================================

    review = relationship(
        "Review",
        back_populates="issue_analysis",
    )


# ============================================================
# RISK DETECTION
# ============================================================

class RiskDetection(Base):

    __tablename__ = "risk_detection"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # REVIEW
    # ========================================================

    review_id = Column(
        Integer,
        ForeignKey(
            "reviews.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )

    # ========================================================
    # RISK FLAG
    # ========================================================

    risk_flag = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # ========================================================
    # RISK LEVEL
    # ========================================================

    risk_level = Column(
        String(50),
        nullable=True,
        index=True,
    )

    """
    Giá trị:

    LOW
    MEDIUM
    HIGH
    """

    # ========================================================
    # RISK KEYWORD
    # ========================================================

    risk_keyword = Column(
        String(255),
        nullable=True,
    )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # ========================================================
    # RELATIONSHIP
    # ========================================================

    review = relationship(
        "Review",
        back_populates="risk_detection",
    )


# ============================================================
# ANALYSIS HISTORY
# ============================================================

class AnalysisHistory(Base):

    __tablename__ = "analysis_history"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # PRODUCT
    # ========================================================

    product_id = Column(
        Integer,
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # REVIEW STATISTICS
    # ========================================================

    total_reviews = Column(
        Integer,
        nullable=False,
        default=0,
    )

    analyzed_reviews = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # ========================================================
    # SENTIMENT COUNTS
    # ========================================================

    positive_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    negative_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    neutral_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # ========================================================
    # SENTIMENT RATES
    # ========================================================

    positive_rate = Column(
        Float,
        nullable=False,
        default=0,
    )

    negative_rate = Column(
        Float,
        nullable=False,
        default=0,
    )

    neutral_rate = Column(
        Float,
        nullable=False,
        default=0,
    )

    # ========================================================
    # ISSUE / RISK SNAPSHOT
    # ========================================================

    issue_summary = Column(
        Text,
        nullable=True,
    )

    risk_summary = Column(
        Text,
        nullable=True,
    )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    analyzed_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # ========================================================
    # RELATIONSHIP
    # ========================================================

    product = relationship(
        "Product",
        back_populates="analysis_history",
    )

    # ========================================================
    # INDEX
    # ========================================================

    __table_args__ = (

        Index(
            "ix_analysis_history_product_date",
            "product_id",
            "analyzed_at",
        ),

    )
