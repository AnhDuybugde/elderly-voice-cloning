"""Intelligibility check: ASR transcription (faster-whisper) + Vietnamese CER.

Used by the QC gate to catch TTS hallucinations (skipped / repeated words) and
DSP settings that make speech unintelligible. The ASR model is a fixed, cached
version so the "ruler" does not change between runs.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Optional

import numpy as np

DEFAULT_ASR_MODEL = os.environ.get("EVC_ASR_MODEL", "small")
# Biases the ASR towards the product wake-word so CER reflects speech quality, not a name
ASR_CONTEXT_PROMPT = "Gia An là trợ lý giọng nói trong nhà."

# Pure hesitation sounds inserted by the text humanizer (never part of the label)
_FILLERS = {"ờ", "à", "ừ", "ừm", "ơ", "ư", "ậm"}

# Regional words <-> standard words. Whisper tends to "standardize" dialect speech
# ("tui" -> "tôi", "hông" -> "không"), which is an ASR artefact, not a TTS error, so both
# reference and hypothesis are mapped to one canonical form before scoring.
_DIALECT_CANON = {
    "tui": "tôi", "hông": "không", "hổng": "không", "nghen": "nghe", "vô": "vào", "giùm": "giúp",
    "ni": "nay", "nớ": "đó", "rứa": "vậy", "mô": "đâu", "răng": "sao", "mạ": "mẹ", "má": "mẹ",
    "té": "ngã", "biểu": "bảo", "coi": "xem", "nhá": "nhé", "nha": "nhé",
}


def _expand_numbers(text: str) -> str:
    """Spell out digits / times the same way the TTS front-end does ("8h" -> "tám giờ")."""
    if not re.search(r"\d", text):
        return text
    try:
        from zerotts.text_norm import normalize_vi_text

        return normalize_vi_text(text)
    except Exception:
        return text


def normalize_vi(text: str, drop_fillers: bool = False, canonical: bool = True) -> str:
    """Lowercase, NFC, spell out numbers, strip punctuation; optionally drop fillers and
    map regional words to a canonical standard form."""
    text = unicodedata.normalize("NFC", _expand_numbers(text or "")).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    words = text.split()
    if drop_fillers:
        words = [w for w in words if w not in _FILLERS]
    if canonical:
        words = [_DIALECT_CANON.get(w, w) for w in words]
    return " ".join(words)


def _levenshtein(a: list, b: list) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def cer(reference: str, hypothesis: str, drop_fillers: bool = True) -> float:
    """Character error rate (spaces removed) between normalized texts."""
    ref = normalize_vi(reference, drop_fillers).replace(" ", "")
    hyp = normalize_vi(hypothesis, drop_fillers).replace(" ", "")
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(list(ref), list(hyp)) / len(ref)


def wer(reference: str, hypothesis: str, drop_fillers: bool = True) -> float:
    ref = normalize_vi(reference, drop_fillers).split()
    hyp = normalize_vi(hypothesis, drop_fillers).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)


class VietnameseASR:
    """Lazy faster-whisper wrapper (GPU int8_float16 if available, else CPU int8)."""

    _model = None
    _model_name = None

    def __init__(self, model_name: str = DEFAULT_ASR_MODEL):
        self.model_name = model_name

    def _load(self):
        if VietnameseASR._model is None or VietnameseASR._model_name != self.model_name:
            from faster_whisper import WhisperModel
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                try:
                    VietnameseASR._model = WhisperModel(self.model_name, device="cuda", compute_type="int8_float16")
                except Exception:
                    VietnameseASR._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            else:
                VietnameseASR._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            VietnameseASR._model_name = self.model_name
        return VietnameseASR._model

    def transcribe(self, audio: np.ndarray, sr: int) -> str:
        import librosa

        model = self._load()
        y = np.asarray(audio, dtype=np.float32)
        if sr != 16000:
            y = librosa.resample(y, orig_sr=sr, target_sr=16000)
        try:
            return self._run(model, y)
        except RuntimeError as exc:  # e.g. CUDA runtime libs (libcublas) missing -> CPU
            if "cuda" not in str(exc).lower() and "cublas" not in str(exc).lower():
                raise
            from faster_whisper import WhisperModel

            VietnameseASR._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            return self._run(VietnameseASR._model, y)

    @staticmethod
    def _run(model, y: np.ndarray) -> str:
        segments, _ = model.transcribe(
            y, language="vi", beam_size=5, vad_filter=False, condition_on_previous_text=False,
            initial_prompt=ASR_CONTEXT_PROMPT,
        )
        return " ".join(s.text.strip() for s in segments).strip()


def measure_intelligibility(
    audio: np.ndarray,
    sr: int,
    reference_text: str,
    asr: Optional[VietnameseASR] = None,
) -> dict[str, float | str]:
    asr = asr or VietnameseASR()
    hyp = asr.transcribe(audio, sr)
    return {"asr_text": hyp, "cer": round(cer(reference_text, hyp), 4), "wer": round(wer(reference_text, hyp), 4)}
