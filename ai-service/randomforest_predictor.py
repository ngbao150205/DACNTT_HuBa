import os
import pickle


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "randomforest"
)



with open(
    os.path.join(
        MODEL_PATH,
        "best_sentiment_model.pkl"
    ),
    "rb"
) as f:

    rf_model = pickle.load(f)



with open(
    os.path.join(
        MODEL_PATH,
        "vectorizer.pkl"
    ),
    "rb"
) as f:

    vectorizer = pickle.load(f)



def predict_randomforest(text):

    vector = vectorizer.transform(
        [text]
    )


    result = rf_model.predict(
        vector
    )[0]


    return {
        "label": result,
        "confidence": None
    }