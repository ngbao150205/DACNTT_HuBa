import os
import requests

from dotenv import load_dotenv

from app.services.decision_layer import decide_result

load_dotenv()


AI_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")


class UnanalyzableReview(ValueError):
    """The review has no text usable by the sentiment model."""


def predict_sentiment(
    text: str,
    rating: int | float | None = None
):
    if not text or not text.strip():
        raise UnanalyzableReview("Review text is empty after preprocessing")

    payload = {
        "text": text
    }

    if rating is not None:
        payload["rating"] = rating

    response = requests.post(
        f"{AI_URL}/predict",
        json=payload,
        timeout=60
    )

    if response.status_code == 422:
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if detail == "Review text is empty after preprocessing":
            raise UnanalyzableReview(detail)

    response.raise_for_status()

    ai_result = response.json()
    if not isinstance(ai_result, dict):
        raise ValueError("AI result must be a dictionary")
    model_result = ai_result.get("final")
    final_result = decide_result(text=text, rating=rating, model_result=model_result)
    return {
        **ai_result,
        **final_result,
        "model_result": model_result,
        "final": final_result,
    }
