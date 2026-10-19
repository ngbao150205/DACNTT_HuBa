import numpy as np

from tensorflow.keras.preprocessing.sequence import pad_sequences

from preprocessing import preprocess_keras
from model_loader import keras_model


def predict_keras(text):
    text = preprocess_keras(text)

    tokenizer = keras_model["tokenizer"]
    model = keras_model["model"]
    encoder = keras_model["encoder"]

    max_len = int(
        keras_model["config"]["max_len"]
    )

    sequence = tokenizer.texts_to_sequences(
        [text]
    )

    padded = pad_sequences(
        sequence,
        maxlen=max_len,
        padding="post",
        truncating="post"
    )

    prediction = model.predict(
        padded,
        verbose=0
    )[0]

    index = int(
        np.argmax(prediction)
    )

    label = encoder.inverse_transform(
        [index]
    )[0]

    confidence = float(
        np.max(prediction)
    )

    return {
        "label": label,
        "sentiment": label,
        "confidence": confidence,
        "model_name": "keras_sentiment_model"
    }