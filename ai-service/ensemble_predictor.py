from deep_learning_predictor import (
    predict_fasttext,
    predict_keras
)

from decision_layer import decide_result



def ensemble_predict(text):


    fasttext_result = predict_fasttext(
        text
    )


    keras_result = predict_keras(
        text
    )


    final_result = decide_result(
    fasttext_result,
    keras_result,
)


    return {

        "text": text,

        "fasttext": fasttext_result,

        "keras": keras_result,

        "final": final_result
    }