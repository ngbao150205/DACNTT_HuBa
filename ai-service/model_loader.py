import os
import pickle
import json
import tensorflow as tf


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


MODELS_DIR = os.path.join(
    BASE_DIR,
    "models"
)



def load_fasttext_model():

    path = os.path.join(
        MODELS_DIR,
        "fasttext_bilstm_v3"
    )


    model = tf.keras.models.load_model(
        os.path.join(
            path,
            "model.keras"
        )
    )


    with open(
        os.path.join(path, "tokenizer.pkl"),
        "rb"
    ) as f:
        tokenizer = pickle.load(f)


    with open(
        os.path.join(path, "label_encoder.pkl"),
        "rb"
    ) as f:
        encoder = pickle.load(f)


    with open(
        os.path.join(path, "config.json"),
        "r",
        encoding="utf-8"
    ) as f:
        config = json.load(f)


    return {
        "model": model,
        "tokenizer": tokenizer,
        "encoder": encoder,
        "config": config
    }



def load_keras_model():

    path = os.path.join(
        MODELS_DIR,
        "keras"
    )


    model = tf.keras.models.load_model(
        os.path.join(
            path,
            "sentiment_lstm_model.keras"
        )
    )


    with open(
        os.path.join(path, "tokenizer.pkl"),
        "rb"
    ) as f:
        tokenizer = pickle.load(f)


    with open(
        os.path.join(path, "label_encoder.pkl"),
        "rb"
    ) as f:
        encoder = pickle.load(f)


    with open(
        os.path.join(path, "preprocess_config.json"),
        "r",
        encoding="utf-8"
    ) as f:
        config = json.load(f)


    return {
        "model": model,
        "tokenizer": tokenizer,
        "encoder": encoder,
        "config": config
    }



fasttext_model = load_fasttext_model()

keras_model = load_keras_model()