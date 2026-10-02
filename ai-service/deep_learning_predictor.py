import numpy as np

from tensorflow.keras.preprocessing.sequence import pad_sequences

from preprocessing import (
    preprocess_fasttext,
    preprocess_keras
)

from model_loader import (
    fasttext_model,
    keras_model
)



def predict_model(
    text,
    package,
    preprocess_func
):

    text = preprocess_func(text)


    tokenizer = package["tokenizer"]

    model = package["model"]

    encoder = package["encoder"]

    max_len = int(
        package["config"]["max_len"]
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


    index = np.argmax(
        prediction
    )


    label = encoder.inverse_transform(
        [index]
    )[0]


    confidence = float(
        np.max(prediction)
    )


    return {
        "label": label,
        "confidence": confidence
    }




def predict_fasttext(text):

    return predict_model(
        text,
        fasttext_model,
        preprocess_fasttext
    )



def predict_keras(text):

    return predict_model(
        text,
        keras_model,
        preprocess_keras
    )