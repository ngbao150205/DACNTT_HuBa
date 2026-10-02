def decide_result(
    fasttext_result,
    keras_result
):

    fast_label = fasttext_result["label"]
    keras_label = keras_result["label"]


    fast_conf = fasttext_result["confidence"]
    keras_conf = keras_result["confidence"]



    # ==========================
    # CASE 1:
    # Hai model cùng dự đoán
    # ==========================

    if fast_label == keras_label:

        return {

            "sentiment": fast_label,

            "confidence": max(
                fast_conf,
                keras_conf
            ),

            "method": "model_agreement"
        }



    # ==========================
    # CASE 2:
    # Hai model khác nhau
    # Chọn confidence cao hơn
    # ==========================

    if fast_conf > keras_conf:

        return {

            "sentiment": fast_label,

            "confidence": fast_conf,

            "method": "fasttext_higher_confidence"

        }


    else:

        return {

            "sentiment": keras_label,

            "confidence": keras_conf,

            "method": "keras_higher_confidence"

        }