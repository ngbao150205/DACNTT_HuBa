from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from custom_vocab_predictor import get_predictor, MODEL_NAME

predictor = get_predictor()
# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Underthesea Custom Vocab V3 Sentiment AI",
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
        "version": "1.0.0",
        "model_name": MODEL_NAME,
        "checkpoints": predictor.checkpoints,
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model_name": MODEL_NAME,
        "checkpoints": predictor.checkpoints,
    }


# =========================================================
# PREDICT
# =========================================================

@app.post("/predict")
def predict(
    review: ReviewRequest
):
    try:
        result = predictor.predict(
            text=review.text,
            rating=review.rating
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
