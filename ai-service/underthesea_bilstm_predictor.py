import json
import pickle
import re
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
try:
    import keras
except ModuleNotFoundError:
    from tensorflow import keras
from underthesea import word_tokenize


class UndertheseaBiLSTMPredictor:
    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)

        self.model_path = self.model_dir / "model.keras"
        self.tokenizer_path = self.model_dir / "tokenizer.pkl"
        self.label_encoder_path = self.model_dir / "label_encoder.pkl"
        self.config_path = self.model_dir / "config.json"

        self.config = self._load_config()
        self.vocab = self._load_vocab()
        self.label_encoder = self._load_label_encoder()

        self.model = keras.models.load_model(
            self.model_path,
            compile=False
        )

        self.max_len = int(self.config.get("max_len", 120))
        self.padding = self.config.get("padding", "post")
        self.truncating = self.config.get("truncating", "pre")
        self.vi_keep = self.config.get(
            "vi_keep",
            "0-9a-zA-Záàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
        )

        self.pad_id = self.vocab.get("<PAD>", 0)
        self.oov_id = self.vocab.get("<OOV>", 1)

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _load_vocab(self) -> Dict[str, int]:
        with open(self.tokenizer_path, "rb") as file:
            vocab = pickle.load(file)

        if not isinstance(vocab, dict):
            raise TypeError("tokenizer.pkl must be a dict token -> id")

        return vocab

    def _load_label_encoder(self):
        with open(self.label_encoder_path, "rb") as file:
            return pickle.load(file)

    def _normalize_text(self, text: str) -> str:
        text = text.lower().strip()

        allowed_pattern = f"[^{self.vi_keep}\\s]"
        text = re.sub(allowed_pattern, " ", text)

        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _tokenize(self, text: str) -> List[str]:
        normalized_text = self._normalize_text(text)

        tokenized_text = word_tokenize(
            normalized_text,
            format="text"
        )

        return tokenized_text.split()

    def _tokens_to_ids(self, tokens: List[str]) -> List[int]:
        return [
            self.vocab.get(token, self.oov_id)
            for token in tokens
        ]

    def _pad_sequence(self, sequence: List[int]) -> List[int]:
        if len(sequence) > self.max_len:
            if self.truncating == "pre":
                sequence = sequence[-self.max_len:]
            else:
                sequence = sequence[:self.max_len]

        if len(sequence) < self.max_len:
            pad_length = self.max_len - len(sequence)

            if self.padding == "post":
                sequence = sequence + [self.pad_id] * pad_length
            else:
                sequence = [self.pad_id] * pad_length + sequence

        return sequence

    def preprocess(self, text: str) -> np.ndarray:
        tokens = self._tokenize(text)
        token_ids = self._tokens_to_ids(tokens)
        padded_ids = self._pad_sequence(token_ids)

        return np.array([padded_ids], dtype=np.int32)

    def predict(self, text: str) -> Dict[str, Any]:
        input_ids = self.preprocess(text)

        probabilities = self.model.predict(
            input_ids,
            verbose=0
        )[0]

        predicted_index = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_index])

        sentiment = self.label_encoder.inverse_transform(
            [predicted_index]
        )[0]

        return {
            "sentiment": str(sentiment),
            "confidence": confidence,
            "probabilities": {
                str(label): float(prob)
                for label, prob in zip(
                    self.label_encoder.classes_,
                    probabilities
                )
            },
            "model_name": "underthesea_bilstm_attention"
        }