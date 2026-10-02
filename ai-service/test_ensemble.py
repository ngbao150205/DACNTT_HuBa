from ensemble_predictor import ensemble_predict



reviews = [

"Sản phẩm rất đẹp, giao hàng nhanh",

"Sản phẩm bị lỗi, chất lượng tệ",

"Sản phẩm bình thường"

]


for review in reviews:

    print("====================")

    print(
        ensemble_predict(review)
    )