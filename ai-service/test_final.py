from ensemble_predictor import ensemble_predict



reviews = [

    "Sản phẩm rất đẹp, giao hàng nhanh",

    "Sản phẩm bị lỗi, chất lượng rất tệ",

    "Sản phẩm bình thường",

    "Sản phẩm rất tốt, tôi rất hài lòng",

    "Giao hàng quá chậm, chờ rất lâu",

    "Sản phẩm đẹp nhưng bị hỏng sau 2 ngày"

]



for review in reviews:

    print("==============================")

    print("Review:")
    print(review)


    result = ensemble_predict(
        review
    )


    print("\nFastText:")
    print(
        result["fasttext"]
    )


    print("\nKeras:")
    print(
        result["keras"]
    )


    print("\nFINAL:")
    print(
        result["final"]
    )