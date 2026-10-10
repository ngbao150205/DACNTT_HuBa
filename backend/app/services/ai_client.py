import os
import requests

from dotenv import load_dotenv

load_dotenv()


AI_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")


def predict_sentiment(
    text: str,
    rating: int | float | None = None
):
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

    response.raise_for_status()

    return response.json()