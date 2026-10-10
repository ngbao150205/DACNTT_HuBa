from deep_learning_predictor import (
    predict_fasttext,
    predict_keras
)

from decision_layer import decide_result


def ensemble_predict(
    text,
    rating=None
):
    fasttext_result = predict_fasttext(
        text
    )

    keras_result = predict_keras(
        text
    )

    final_result = decide_result(
        text=text,
        rating=rating,
        fasttext_result=fasttext_result,
        keras_result=keras_result,
    )

    return {
    "text": text,
    "rating": rating,

    "sentiment": final_result.get("sentiment"),
    "confidence": final_result.get("confidence"),
    "method": final_result.get("method"),
    "decision_method": final_result.get("decision_method"),
    "raw_sentiment": final_result.get("raw_sentiment"),
    "raw_confidence": final_result.get("raw_confidence"),
    "rating_conflict": final_result.get("rating_conflict", False),
    "evidence": final_result.get("evidence", {}),

    "fasttext": fasttext_result,
    "keras": keras_result,
    "final": final_result,
}