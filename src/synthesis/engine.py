"""Speech synthesis engines: ZeroTTS wrapper and extensible synthesizer interface."""

from __future__ import annotations

import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa


class BaseSynthesizer(ABC):
    """Abstract base class for speech synthesizers."""

    @abstractmethod
    def synthesize(self, text: str, voice: str, target_sr: int = 24000) -> tuple[np.ndarray, int]:
        """Synthesize text to audio array and sample rate."""
        pass


class ZeroTTSSynthesizer(BaseSynthesizer):
    """ZeroTTS local onnx-based neural speech synthesizer."""

    def __init__(self):
        self._check_installed()

    def _check_installed(self) -> bool:
        try:
            import zerotts
            return True
        except ImportError:
            return False

    def synthesize(self, text: str, voice: str = "huuduc", target_sr: int = 24000) -> tuple[np.ndarray, int]:
        """Synthesizes text into audio array at target_sr.

        Uses zerotts command line or python API.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # zerotts say <text> -v <voice> -o <tmp_path>
            cmd = ["zerotts", "say", text, "-v", voice, "-o", tmp_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0 or not os.path.exists(tmp_path):
                raise RuntimeError(f"ZeroTTS synthesis failed: {result.stderr}")

            # Read generated audio
            audio, sr = sf.read(tmp_path)
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            # Resample if needed
            if sr != target_sr:
                audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=target_sr)
                sr = target_sr

            # Normalize
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val * 0.90

            return audio.astype(np.float32), target_sr

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class FallbackSynthesizer(BaseSynthesizer):
    """Procedural fallback synthesizer for unit tests or environments without ZeroTTS."""

    def synthesize(self, text: str, voice: str = "huuduc", target_sr: int = 24000) -> tuple[np.ndarray, int]:
        # Generate speech-like harmonic tone with duration proportional to text length
        duration = max(1.5, len(text.split()) * 0.35)
        n_samples = int(duration * target_sr)
        t = np.arange(n_samples) / target_sr

        base_f0 = 120.0 if "nam" in voice or voice == "huuduc" else 190.0
        # Harmonic series
        y = (
            0.5 * np.sin(2 * np.pi * base_f0 * t)
            + 0.3 * np.sin(2 * np.pi * (2 * base_f0) * t)
            + 0.15 * np.sin(2 * np.pi * (3 * base_f0) * t)
        )
        # Apply speech envelope
        mod = 0.5 * (1.0 + np.sin(2 * np.pi * 3.5 * t))
        y = y * mod
        return y.astype(np.float32), target_sr


def get_synthesizer(prefer_local: bool = True) -> BaseSynthesizer:
    try:
        synth = ZeroTTSSynthesizer()
        return synth
    except Exception:
        return FallbackSynthesizer()
