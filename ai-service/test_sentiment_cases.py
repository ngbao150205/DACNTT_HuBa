from deep_learning_predictor import (
    predict_fasttext,
    predict_keras
)

from ensemble_predictor import ensemble_predict


# =========================================================
# TEST DATA
# =========================================================

TEST_CASES = [

    # =====================================================
    # POSITIVE
    # =====================================================

    {
        "text": "Sản phẩm rất đẹp",
        "actual": "Positive"
    },
    {
        "text": "Chất lượng sản phẩm rất tốt",
        "actual": "Positive"
    },
    {
        "text": "Tôi rất hài lòng với sản phẩm",
        "actual": "Positive"
    },
    {
        "text": "Sản phẩm tuyệt vời",
        "actual": "Positive"
    },
    {
        "text": "Hàng đẹp, đúng như mô tả",
        "actual": "Positive"
    },
    {
        "text": "Giao hàng nhanh, đóng gói cẩn thận",
        "actual": "Positive"
    },
    {
        "text": "Sản phẩm dùng rất thích",
        "actual": "Positive"
    },
    {
        "text": "Tôi rất ưng ý sản phẩm này",
        "actual": "Positive"
    },
    {
        "text": "Chất lượng tốt, rất đáng tiền",
        "actual": "Positive"
    },
    {
        "text": "Sản phẩm đẹp và hoạt động tốt",
        "actual": "Positive"
    },


    # =====================================================
    # NEGATIVE
    # =====================================================

    {
        "text": "Sản phẩm rất dở",
        "actual": "Negative"
    },
    {
        "text": "Dở tệ",
        "actual": "Negative"
    },
    {
        "text": "Chất lượng sản phẩm rất tệ",
        "actual": "Negative"
    },
    {
        "text": "Sản phẩm bị lỗi",
        "actual": "Negative"
    },
    {
        "text": "Hàng bị hỏng",
        "actual": "Negative"
    },
    {
        "text": "Không đáng tiền",
        "actual": "Negative"
    },
    {
        "text": "Tôi rất thất vọng về sản phẩm",
        "actual": "Negative"
    },
    {
        "text": "Giao hàng quá chậm",
        "actual": "Negative"
    },
    {
        "text": "Chất lượng quá kém",
        "actual": "Negative"
    },
    {
        "text": "Sản phẩm tệ, không nên mua",
        "actual": "Negative"
    },


    # =====================================================
    # NEUTRAL
    # =====================================================

    {
        "text": "Sản phẩm bình thường",
        "actual": "Neutral"
    },
    {
        "text": "Sản phẩm không có gì đặc biệt",
        "actual": "Neutral"
    },
    {
        "text": "Sản phẩm đúng mô tả",
        "actual": "Neutral"
    },
    {
        "text": "Chất lượng ở mức bình thường",
        "actual": "Neutral"
    },
    {
        "text": "Sản phẩm dùng được",
        "actual": "Neutral"
    },
    {
        "text": "Mọi thứ ổn",
        "actual": "Neutral"
    },
    {
        "text": "Không tốt cũng không xấu",
        "actual": "Neutral"
    },
    {
        "text": "Sản phẩm như mong đợi",
        "actual": "Neutral"
    },
    {
        "text": "Hàng nhận được đúng sản phẩm đã đặt",
        "actual": "Neutral"
    },
    {
        "text": "Chưa thấy có gì nổi bật",
        "actual": "Neutral"
    }

]


# =========================================================
# HELPER
# =========================================================

def is_correct(predicted, actual):
    return predicted == actual


def calculate_accuracy(results, key):

    correct = sum(
        1
        for result in results
        if result[key] == result["actual"]
    )

    total = len(results)

    return correct, total, correct / total


# =========================================================
# RUN TEST
# =========================================================

results = []


print("\n")
print("=" * 90)
print("SENTIMENT MODEL TEST")
print("=" * 90)


for index, case in enumerate(TEST_CASES, start=1):

    text = case["text"]
    actual = case["actual"]


    # -------------------------
    # FastText
    # -------------------------

    fasttext_result = predict_fasttext(text)


    # -------------------------
    # Keras
    # -------------------------

    keras_result = predict_keras(text)


    # -------------------------
    # Ensemble
    # -------------------------

    ensemble_result = ensemble_predict(text)

    final_result = ensemble_result["final"]


    # -------------------------
    # Extract
    # -------------------------

    fasttext_label = fasttext_result["label"]
    fasttext_conf = fasttext_result["confidence"]

    keras_label = keras_result["label"]
    keras_conf = keras_result["confidence"]

    ensemble_label = final_result["sentiment"]
    ensemble_conf = final_result["confidence"]

    method = final_result.get(
        "method",
        ""
    )


    # -------------------------
    # Store
    # -------------------------

    result = {

        "text": text,

        "actual": actual,

        "fasttext": fasttext_label,

        "fasttext_conf": fasttext_conf,

        "keras": keras_label,

        "keras_conf": keras_conf,

        "ensemble": ensemble_label,

        "ensemble_conf": ensemble_conf,

        "method": method
    }


    results.append(result)


    # =====================================================
    # PRINT CASE
    # =====================================================

    print("\n" + "-" * 90)

    print(
        f"CASE {index}/"
        f"{len(TEST_CASES)}"
    )

    print(
        f"Review : {text}"
    )

    print(
        f"Actual : {actual}"
    )


    print(
        f"FastText : "
        f"{fasttext_label:<8} "
        f"confidence={fasttext_conf:.4f} "
        f"{'OK' if is_correct(fasttext_label, actual) else 'WRONG'}"
    )


    print(
        f"Keras    : "
        f"{keras_label:<8} "
        f"confidence={keras_conf:.4f} "
        f"{'OK' if is_correct(keras_label, actual) else 'WRONG'}"
    )


    print(
        f"Ensemble : "
        f"{ensemble_label:<8} "
        f"confidence={ensemble_conf:.4f} "
        f"{'OK' if is_correct(ensemble_label, actual) else 'WRONG'}"
    )


    print(
        f"Method   : {method}"
    )


# =========================================================
# OVERALL ACCURACY
# =========================================================

fasttext_correct, total, fasttext_accuracy = (
    calculate_accuracy(
        results,
        "fasttext"
    )
)


keras_correct, _, keras_accuracy = (
    calculate_accuracy(
        results,
        "keras"
    )
)


ensemble_correct, _, ensemble_accuracy = (
    calculate_accuracy(
        results,
        "ensemble"
    )
)


# =========================================================
# SUMMARY
# =========================================================

print("\n")
print("=" * 90)
print("OVERALL SUMMARY")
print("=" * 90)


print(
    f"Total cases : {total}"
)


print(
    f"FastText    : "
    f"{fasttext_correct}/{total} "
    f"({fasttext_accuracy:.2%})"
)


print(
    f"Keras       : "
    f"{keras_correct}/{total} "
    f"({keras_accuracy:.2%})"
)


print(
    f"Ensemble    : "
    f"{ensemble_correct}/{total} "
    f"({ensemble_accuracy:.2%})"
)


# =========================================================
# ACCURACY BY CLASS
# =========================================================

print("\n")
print("=" * 90)
print("ACCURACY BY SENTIMENT")
print("=" * 90)


for sentiment in [
    "Positive",
    "Negative",
    "Neutral"
]:

    class_results = [
        result
        for result in results
        if result["actual"] == sentiment
    ]


    class_total = len(
        class_results
    )


    fast_correct = sum(
        1
        for result in class_results
        if result["fasttext"] == sentiment
    )


    keras_correct_class = sum(
        1
        for result in class_results
        if result["keras"] == sentiment
    )


    ensemble_correct_class = sum(
        1
        for result in class_results
        if result["ensemble"] == sentiment
    )


    print(
        f"\n{sentiment}"
    )


    print(
        f"  FastText : "
        f"{fast_correct}/{class_total} "
        f"({fast_correct / class_total:.2%})"
    )


    print(
        f"  Keras    : "
        f"{keras_correct_class}/{class_total} "
        f"({keras_correct_class / class_total:.2%})"
    )


    print(
        f"  Ensemble : "
        f"{ensemble_correct_class}/{class_total} "
        f"({ensemble_correct_class / class_total:.2%})"
    )


# =========================================================
# MODEL AGREEMENT
# =========================================================

agreement_cases = [
    result
    for result in results
    if result["fasttext"] == result["keras"]
]


disagreement_cases = [
    result
    for result in results
    if result["fasttext"] != result["keras"]
]


print("\n")
print("=" * 90)
print("MODEL AGREEMENT")
print("=" * 90)


print(
    f"Agreement    : "
    f"{len(agreement_cases)}/{total}"
)


print(
    f"Disagreement : "
    f"{len(disagreement_cases)}/{total}"
)


# =========================================================
# ENSEMBLE IMPROVEMENT ANALYSIS
# =========================================================

ensemble_fixed = []

ensemble_broke = []


for result in results:

    fast_correct = (
        result["fasttext"] == result["actual"]
    )

    keras_correct = (
        result["keras"] == result["actual"]
    )

    ensemble_correct = (
        result["ensemble"] == result["actual"]
    )


    # Ensemble sửa được lỗi của ít nhất một model
    if (
        ensemble_correct
        and
        not fast_correct
        and
        not keras_correct
    ):
        ensemble_fixed.append(result)


    # Ensemble làm sai trong khi ít nhất
    # một model ban đầu đúng
    if (
        not ensemble_correct
        and
        (
            fast_correct
            or keras_correct
        )
    ):
        ensemble_broke.append(result)


print("\n")
print("=" * 90)
print("ENSEMBLE ANALYSIS")
print("=" * 90)


print(
    f"Ensemble fixed cases : "
    f"{len(ensemble_fixed)}"
)


print(
    f"Ensemble broke cases : "
    f"{len(ensemble_broke)}"
)


# =========================================================
# DETAILS: ENSEMBLE BROKE CORRECT MODEL
# =========================================================

if ensemble_broke:

    print("\n")
    print("=" * 90)
    print("CASES WHERE ENSEMBLE MADE A CORRECT MODEL WRONG")
    print("=" * 90)


    for result in ensemble_broke:

        print(
            f"\nReview : {result['text']}"
        )

        print(
            f"Actual : {result['actual']}"
        )

        print(
            f"FastText : "
            f"{result['fasttext']} "
            f"({result['fasttext_conf']:.4f})"
        )

        print(
            f"Keras    : "
            f"{result['keras']} "
            f"({result['keras_conf']:.4f})"
        )

        print(
            f"Ensemble : "
            f"{result['ensemble']} "
            f"({result['ensemble_conf']:.4f})"
        )

        print(
            f"Method   : "
            f"{result['method']}"
        )


# =========================================================
# DETAILS: BOTH MODELS WRONG BUT ENSEMBLE RIGHT
# =========================================================

if ensemble_fixed:

    print("\n")
    print("=" * 90)
    print("CASES WHERE ENSEMBLE FIXED BOTH MODELS")
    print("=" * 90)


    for result in ensemble_fixed:

        print(
            f"\nReview : {result['text']}"
        )

        print(
            f"Actual : {result['actual']}"
        )

        print(
            f"FastText : "
            f"{result['fasttext']} "
            f"({result['fasttext_conf']:.4f})"
        )

        print(
            f"Keras    : "
            f"{result['keras']} "
            f"({result['keras_conf']:.4f})"
        )

        print(
            f"Ensemble : "
            f"{result['ensemble']} "
            f"({result['ensemble_conf']:.4f})"
        )

        print(
            f"Method   : "
            f"{result['method']}"
        )


# =========================================================
# WRONG CASES
# =========================================================

wrong_ensemble = [
    result
    for result in results
    if result["ensemble"] != result["actual"]
]


print("\n")
print("=" * 90)
print("ALL ENSEMBLE ERRORS")
print("=" * 90)


for result in wrong_ensemble:

    print(
        f"\nReview : {result['text']}"
    )

    print(
        f"Actual : {result['actual']}"
    )

    print(
        f"FastText : "
        f"{result['fasttext']} "
        f"({result['fasttext_conf']:.4f})"
    )

    print(
        f"Keras    : "
        f"{result['keras']} "
        f"({result['keras_conf']:.4f})"
    )

    print(
        f"Ensemble : "
        f"{result['ensemble']} "
        f"({result['ensemble_conf']:.4f})"
    )

    print(
        f"Method   : "
        f"{result['method']}"
    )


# =========================================================
# FINAL
# =========================================================

print("\n")
print("=" * 90)
print("TEST COMPLETED")
print("=" * 90)