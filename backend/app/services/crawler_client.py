import requests


CRAWLER_URL = "http://localhost:8002"


def crawl_product(url: str):

    response = requests.post(
        f"{CRAWLER_URL}/crawl",
        json={
            "url": url
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()