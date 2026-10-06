import requests


AI_URL = "http://localhost:8001"



def predict_sentiment(text:str):

    response = requests.post(

        f"{AI_URL}/predict",

        json={
            "text":text
        },

        timeout=60
    )


    response.raise_for_status()


    return response.json()