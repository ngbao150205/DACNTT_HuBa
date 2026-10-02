from model_loader import (
    fasttext_model,
    keras_model
)


words = [
    "tởm",
    "tệ",
    "đẹp",
    "hỏng",
    "bình thường"
]


print("================")
print("FASTTEXT TOKENIZER")
print("================")


fasttext_tokenizer = fasttext_model["tokenizer"]


for word in words:

    result = fasttext_tokenizer.texts_to_sequences(
        [word]
    )

    print(
        word,
        "=>",
        result
    )



print("================")
print("KERAS TOKENIZER")
print("================")


keras_tokenizer = keras_model["tokenizer"]


for word in words:

    result = keras_tokenizer.texts_to_sequences(
        [word]
    )

    print(
        word,
        "=>",
        result
    )