from deep_learning_predictor import (
    predict_fasttext,
    predict_keras
)

from randomforest_predictor import (
    predict_randomforest
)



text = "Sản phẩm rất đẹp, giao hàng nhanh"



print(
    "FastText:",
    predict_fasttext(text)
)


print(
    "Keras:",
    predict_keras(text)
)


print(
    "RandomForest:",
    predict_randomforest(text)
)