"""Speaker-embedding similarity (WavLM x-vector) for identity diversity checks.

Two uses:
- pairwise similarity between speaker centroids -> "are our 12 elders actually 12 people?"
- per-sample similarity to its own speaker centroid -> identity consistency across takes
"""

from __future__ import annotations

import os
from typing import Iterable

import numpy as np

DEFAULT_SV_MODEL = os.environ.get("EVC_SV_MODEL", "microsoft/wavlm-base-plus-sv")


class SpeakerEmbedder:
    _cache: dict = {}

    def __init__(self, model_name: str = DEFAULT_SV_MODEL):
        self.model_name = model_name

    def _load(self):
        if self.model_name not in SpeakerEmbedder._cache:
            from transformers import AutoFeatureExtractor, WavLMForXVector

            fe = AutoFeatureExtractor.from_pretrained(self.model_name)
            model = WavLMForXVector.from_pretrained(self.model_name).eval()
            SpeakerEmbedder._cache[self.model_name] = (fe, model)
        return SpeakerEmbedder._cache[self.model_name]

    def embed(self, audio: np.ndarray, sr: int) -> np.ndarray:
        import librosa
        import torch

        fe, model = self._load()
        y = np.asarray(audio, dtype=np.float32)
        if sr != 16000:
            y = librosa.resample(y, orig_sr=sr, target_sr=16000)
        inputs = fe(y, sampling_rate=16000, return_tensors="pt", padding=True)
        with torch.no_grad():
            emb = model(**inputs).embeddings[0].numpy()
        return emb / (np.linalg.norm(emb) + 1e-12)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def centroid(embeddings: Iterable[np.ndarray]) -> np.ndarray:
    m = np.mean(np.stack(list(embeddings)), axis=0)
    return m / (np.linalg.norm(m) + 1e-12)


def pairwise_similarity(centroids: dict[str, np.ndarray]) -> tuple[list[str], np.ndarray]:
    names = sorted(centroids)
    mat = np.array([[cosine(centroids[a], centroids[b]) for b in names] for a in names])
    return names, mat
