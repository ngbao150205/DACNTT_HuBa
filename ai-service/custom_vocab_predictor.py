"""Inference using only the underthesea_bilstm_custom_vocab_v3 checkpoints."""

import json
import pickle
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import keras
import numpy as np
from underthesea import word_tokenize


MODEL_NAME = "underthesea_bilstm_custom_vocab_v3"
MODEL_DIR = Path(__file__).resolve().parent / "models" / MODEL_NAME
VI_KEEP = (
    "0-9a-zA-Záàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩị"
    "óòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
)
NEGATORS = {"không", "chưa", "chẳng", "chả", "ko", "k", "hok", "hông", "khong", "chăng"}


def clean_text(text: str) -> str:
    """Match the training pipeline for the character branch."""
    text = unicodedata.normalize("NFC", str(text)).lower()
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    text = re.sub(fr"[^{VI_KEEP}\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def merge_negation(tokens: list[str]) -> list[str]:
    merged = []
    index = 0
    while index < len(tokens):
        if tokens[index] in NEGATORS and index + 1 < len(tokens):
            merged.append(tokens[index] + "_" + tokens[index + 1])
            index += 2
        else:
            merged.append(tokens[index])
            index += 1
    return merged


class CustomVocabPredictor:
    def __init__(self, model_dir: str | Path = MODEL_DIR):
        self.model_dir = Path(model_dir)
        with (self.model_dir / "inference_config.json").open(encoding="utf-8") as file:
            self.config = json.load(file)
        with (self.model_dir / "vocab.json").open(encoding="utf-8") as file:
            vocab = json.load(file)
        self.word_vocab = vocab["word"]
        self.char_vocab = vocab["char"]
        with (self.model_dir / "label_encoder.pkl").open("rb") as file:
            self.labels = [str(label) for label in pickle.load(file).classes_]

        self.checkpoints = self.config["checkpoints"]
        self.models = [
            keras.models.load_model(self.model_dir / filename, compile=False)
            for filename in self.checkpoints
        ]
        # The exported architecture defines word_in[64] and char_in[160].
        self.word_length = int(self.models[0].get_layer("word_in").output.shape[-1])
        self.char_length = int(self.models[0].get_layer("char_in").output.shape[-1])
        for model in self.models:
            if (
                int(model.get_layer("word_in").output.shape[-1]) != self.word_length
                or int(model.get_layer("char_in").output.shape[-1]) != self.char_length
                or int(model.output_shape[-1]) != len(self.labels)
                or model.get_layer("emb_a").input_dim != len(self.word_vocab)
                or model.get_layer("emb_b").input_dim != len(self.word_vocab)
                or model.get_layer("emb_c").input_dim != len(self.char_vocab)
            ):
                raise ValueError("Checkpoint inputs, vocabularies or labels do not match")

    def _encode(self, tokens, vocab: dict[str, int], length: int) -> np.ndarray:
        return keras.utils.pad_sequences(
            [[vocab.get(token, vocab["<OOV>"]) for token in tokens]],
            maxlen=length,
            dtype="int32",
            padding=self.config["padding"],
            truncating=self.config["truncating"],
            value=vocab["<PAD>"],
        )

    def preprocess(self, text: str) -> dict[str, np.ndarray]:
        normalized = clean_text(text)
        if not normalized:
            raise ValueError("Review text is empty after preprocessing")
        words = merge_negation(word_tokenize(normalized, format="text").split())
        return {
            "word_in": self._encode(words, self.word_vocab, self.word_length),
            "char_in": self._encode(normalized, self.char_vocab, self.char_length),
        }

    def predict(self, text: str, rating: float | None = None) -> dict:
        inputs = self.preprocess(text)
        # Average the five folds of this model; no legacy model or rule override.
        probabilities = np.mean(
            [np.asarray(model(inputs, training=False))[0] for model in self.models],
            axis=0,
        )
        if not np.all(np.isfinite(probabilities)):
            raise RuntimeError("Model returned non-finite probabilities")
        index = int(np.argmax(probabilities))
        sentiment = self.labels[index]
        confidence = float(probabilities[index])
        final = {
            "sentiment": sentiment,
            "confidence": confidence,
            "method": MODEL_NAME,
            "decision_method": "mean_fold_probabilities",
            "model_name": MODEL_NAME,
            "raw_sentiment": sentiment,
            "raw_confidence": confidence,
            "probabilities": {
                label: float(prob) for label, prob in zip(self.labels, probabilities)
            },
        }
        return {
            "text": text,
            "rating": rating,
            **final,
            "checkpoints": self.checkpoints,
            "final": final,
        }


@lru_cache(maxsize=1)
def get_predictor() -> CustomVocabPredictor:
    return CustomVocabPredictor()
