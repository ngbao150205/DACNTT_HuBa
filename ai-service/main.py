from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ensemble_predictor import ensemble_predict
# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Sentiment Ensemble AI",
    description="Customer review sentiment analysis service",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODEL
# =========================================================

class ReviewRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Customer review text"
    )

    rating: Optional[float] = Field(
        default=None,
        ge=1,
        le=5,
        description="Customer rating from 1 to 5"
    )


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "service": "Sentiment AI Service",
        "status": "running",
        "version": "1.0.0"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =========================================================
# PREDICT
# =========================================================

@app.post("/predict")
def predict(
    review: ReviewRequest
):
    try:
        result = ensemble_predict(
            text=review.text,
            rating=review.rating
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )