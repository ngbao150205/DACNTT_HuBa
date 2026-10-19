"""Compatibility entry point; only the new custom-vocab model is used."""

from custom_vocab_predictor import get_predictor


def ensemble_predict(text, rating=None):
    return get_predictor().predict(text=text, rating=rating)
