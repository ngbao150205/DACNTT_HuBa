from model_loader import (
    fasttext_model,
    keras_model
)


words = [
    "kinh",
    "dở",
    "tệ",
    "đẹp",
    "hỏng"
]


print("FASTTEXT VOCAB")

vocab = fasttext_model["tokenizer"].word_index


for word in words:

    print(
        word,
        "=>",
        vocab.get(word)
    )



print("\nKERAS VOCAB")

vocab = keras_model["tokenizer"].word_index


for word in words:

    print(
        word,
        "=>",
        vocab.get(word)
    )