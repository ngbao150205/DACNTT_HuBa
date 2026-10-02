import re



def preprocess_fasttext(text):

    text = str(text).lower()


    text = re.sub(
        r"[^0-9a-zA-Záàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ\s]",
        " ",
        text
    )


    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()


    return text




def preprocess_keras(text):

    text = str(text).lower()


    text = re.sub(
        r"[^a-zA-ZÀ-ỹ\s]",
        " ",
        text
    )


    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()


    return text