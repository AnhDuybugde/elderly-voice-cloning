"""Speech synthesis engine: High-performance in-memory ZeroTTS with latent blending."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
import librosa


class BaseSynthesizer(ABC):
    """Abstract base class for speech synthesizers."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str = "huuduc",
        secondary_voice: Optional[str] = None,
        blend_ratio: float = 1.0,
        cfg_scale: float = 1.15,
        temperature: float = 0.75,
        target_sr: int = 48000,
    ) -> tuple[np.ndarray, int]:
        """Synthesize text to audio array and sample rate."""
        pass


class ZeroTTSSynthesizer(BaseSynthesizer):
    """High-performance in-memory ZeroTTS engine supporting latent vector interpolation."""

    _instance = None
    _tts_model = None

    def __init__(self, intra_op_threads: int = 4):
        self._init_model(intra_op_threads)

    def _init_model(self, threads: int = 4):
        if ZeroTTSSynthesizer._tts_model is None:
            from zerotts.synthesizer import ZeroTTS
            from zerotts import hub

            ZeroTTSSynthesizer._tts_model = ZeroTTS.from_pretrained(
                hub.DEFAULT_REPO_ID,
                intra_op_num_threads=threads,
            )
        self.tts = ZeroTTSSynthesizer._tts_model
        self.native_sr = getattr(self.tts, "sample_rate", 48000)

    def resolve_blended_latent(
        self,
        base_voice: str,
        secondary_voice: Optional[str] = None,
        blend_ratio: float = 1.0,
    ) -> np.ndarray:
        """Create a continuous latent embedding vector for a unique speaker profile."""
        base_emb = self.tts.load_voice(base_voice).emb

        if not secondary_voice or blend_ratio >= 0.99:
            return base_emb

        try:
            sec_emb = self.tts.load_voice(secondary_voice).emb
            # Linear interpolation in latent space
            blended = blend_ratio * base_emb + (1.0 - blend_ratio) * sec_emb
            # Conserve vector norm to keep conditioning energy consistent
            base_norm = np.linalg.norm(base_emb)
            blended_norm = np.linalg.norm(blended) + 1e-8
            blended = blended * (base_norm / blended_norm)
            return blended.astype(np.float32)
        except Exception:
            return base_emb

    def synthesize(
        self,
        text: str,
        voice: str = "huuduc",
        secondary_voice: Optional[str] = None,
        blend_ratio: float = 1.0,
        cfg_scale: float = 1.15,
        temperature: float = 0.75,
        target_sr: int = 48000,
    ) -> tuple[np.ndarray, int]:
        """Synthesizes text into high-fidelity neural audio array in memory."""
        from zerotts.text_norm import normalize_vi_text

        # 1. Normalize Vietnamese text
        norm_text = normalize_vi_text(text)

        # 2. Resolve speaker latent embedding (single or blended)
        latent = self.resolve_blended_latent(voice, secondary_voice, blend_ratio)

        # 3. Direct neural synthesis in memory
        audio = self.tts.synthesize(
            norm_text,
            voice=latent,
            cfg_scale=cfg_scale,
            audio_temperature=temperature,
            audio_topk=30,
            audio_topp=0.92,
            audio_repetition_penalty=1.20,
        )

        if audio.ndim == 2:
            audio = audio[0]

        sr = self.native_sr

        # 4. Optional resample if requested
        if target_sr and target_sr != sr:
            audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=target_sr)
            sr = target_sr

        # 5. Safe normalization
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = (audio / peak) * 0.88

        return audio.astype(np.float32), sr


class FallbackSynthesizer(BaseSynthesizer):
    """Procedural harmonic synthesizer for unit testing environments."""

    def synthesize(
        self,
        text: str,
        voice: str = "huuduc",
        secondary_voice: Optional[str] = None,
        blend_ratio: float = 1.0,
        cfg_scale: float = 1.15,
        temperature: float = 0.75,
        target_sr: int = 48000,
    ) -> tuple[np.ndarray, int]:
        duration = max(2.0, len(text.split()) * 0.35)
        n_samples = int(duration * target_sr)
        t = np.arange(n_samples) / target_sr
        base_f0 = 120.0 if "nam" in voice or voice == "huuduc" else 190.0

        y = (
            0.5 * np.sin(2 * np.pi * base_f0 * t)
            + 0.3 * np.sin(2 * np.pi * (2 * base_f0) * t)
            + 0.15 * np.sin(2 * np.pi * (3 * base_f0) * t)
        )
        mod = 0.5 * (1.0 + np.sin(2 * np.pi * 3.0 * t))
        y = y * mod
        return (y / (np.max(np.abs(y)) + 1e-8) * 0.85).astype(np.float32), target_sr


def get_synthesizer(prefer_local: bool = True) -> BaseSynthesizer:
    try:
        return ZeroTTSSynthesizer()
    except Exception:
        return FallbackSynthesizer()
