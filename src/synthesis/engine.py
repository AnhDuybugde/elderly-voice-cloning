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
        voice_mix: Optional[dict[str, float]] = None,
        latent_seed: Optional[int] = None,
        latent_jitter: float = 0.0,
        seed: Optional[int] = None,
    ) -> tuple[np.ndarray, int]:
        """Synthesize text to audio array and sample rate.

        voice_mix: {voice_name: weight} multi-voice latent mix (overrides voice/secondary_voice).
        latent_seed / latent_jitter: speaker-specific latent perturbation (identity fingerprint).
        seed: sampling seed for reproducible takes.
        """
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
        """Legacy two-voice blend (kept for backward compatibility)."""
        if not secondary_voice or blend_ratio >= 0.99:
            return self.tts.load_voice(base_voice).emb
        return self.resolve_mixed_latent({base_voice: blend_ratio, secondary_voice: 1.0 - blend_ratio})

    def resolve_mixed_latent(
        self,
        voice_mix: dict[str, float],
        latent_seed: Optional[int] = None,
        latent_jitter: float = 0.0,
    ) -> np.ndarray:
        """Weighted mix of N voice latents + optional seeded perturbation, norm-preserving.

        The perturbation is a random direction with relative magnitude `latent_jitter`
        (e.g. 0.06 = 6% of the latent norm), seeded per speaker so the identity is stable.
        """
        items = [(name, float(w)) for name, w in voice_mix.items() if w > 0]
        total = sum(w for _, w in items) or 1.0
        embs, weights = [], []
        for name, w in items:
            try:
                embs.append(self.tts.load_voice(name).emb.astype(np.float32))
                weights.append(w / total)
            except Exception:
                continue
        if not embs:
            raise ValueError(f"No loadable voices in mix {voice_mix}")

        mixed = sum(w * e for w, e in zip(weights, embs))
        ref_norm = sum(w * np.linalg.norm(e) for w, e in zip(weights, embs))

        if latent_jitter > 0 and latent_seed is not None:
            rng = np.random.default_rng(latent_seed)
            direction = rng.standard_normal(mixed.shape).astype(np.float32)
            direction *= np.linalg.norm(mixed) / (np.linalg.norm(direction) + 1e-8)
            mixed = mixed + latent_jitter * direction

        mixed = mixed * (ref_norm / (np.linalg.norm(mixed) + 1e-8))
        return mixed.astype(np.float32)

    def synthesize(
        self,
        text: str,
        voice: str = "huuduc",
        secondary_voice: Optional[str] = None,
        blend_ratio: float = 1.0,
        cfg_scale: float = 1.15,
        temperature: float = 0.75,
        target_sr: int = 48000,
        voice_mix: Optional[dict[str, float]] = None,
        latent_seed: Optional[int] = None,
        latent_jitter: float = 0.0,
        seed: Optional[int] = None,
    ) -> tuple[np.ndarray, int]:
        """Synthesizes text into high-fidelity neural audio array in memory."""
        from zerotts.text_norm import normalize_vi_text

        norm_text = normalize_vi_text(text)

        if voice_mix:
            latent = self.resolve_mixed_latent(voice_mix, latent_seed, latent_jitter)
        else:
            latent = self.resolve_blended_latent(voice, secondary_voice, blend_ratio)

        if seed is not None:  # ZeroTTS samples with numpy's global RNG
            np.random.seed(seed % (2**32))

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
        if target_sr and target_sr != sr:
            audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=target_sr)
            sr = target_sr

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
        voice_mix: Optional[dict[str, float]] = None,
        latent_seed: Optional[int] = None,
        latent_jitter: float = 0.0,
        seed: Optional[int] = None,
    ) -> tuple[np.ndarray, int]:
        rng = np.random.default_rng(seed)
        duration = max(2.0, len(text.split()) * 0.35)
        n_samples = int(duration * target_sr)
        t = np.arange(n_samples) / target_sr
        male_voices = {"huuduc", "giahuy", "quangminh", "tiendat"}
        main = max(voice_mix, key=voice_mix.get) if voice_mix else voice
        base_f0 = 120.0 if ("nam" in main or main in male_voices) else 210.0

        # Harmonic source with a gentle, speech-like F0 contour (syllable-rate wobble)
        f0 = base_f0 * (1.0 + 0.06 * np.sin(2 * np.pi * 1.3 * t) + 0.002 * rng.standard_normal())
        phase = 2 * np.pi * np.cumsum(f0) / target_sr
        y = sum((0.6 / k) * np.sin(k * phase) for k in range(1, 9))
        # Syllable envelope with short gaps so VAD / pause metrics have something to measure
        mod = np.clip(np.sin(2 * np.pi * 2.0 * t), 0.0, None) ** 0.5
        y = y * mod
        return (y / (np.max(np.abs(y)) + 1e-8) * 0.85).astype(np.float32), target_sr


def get_synthesizer(prefer_local: bool = True) -> BaseSynthesizer:
    try:
        return ZeroTTSSynthesizer()
    except Exception:
        return FallbackSynthesizer()
