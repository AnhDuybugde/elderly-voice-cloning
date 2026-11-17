"""Dataset Generator: orchestrates synthesis, aging DSP, noise mixing, and file saving."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import numpy as np
import soundfile as sf

from src.core.config import (
    OUTPUT_DATASET_DIR,
    get_speakers_config,
    get_prompts_config,
)
from src.core.schema import (
    SpeakerProfile,
    PromptCategory,
    AudioSampleMetadata,
)
from src.synthesis.aging_dsp import apply_analog_warmth_and_aging
from src.synthesis.engine import BaseSynthesizer, get_synthesizer
from src.noise.augment import mix_audio_with_noise
from src.metrics.acoustic_features import analyze_audio_sample
from src.pipeline.manifest import (
    export_manifest_jsonl,
    export_manifest_csv,
    generate_summary_report,
)

BENCHMARK_PROMPT = "Xin chào Gia An, Gia An có nghe rõ tôi nói không?"


def slugify(text: str) -> str:
    """Convert text to snake_case ascii string."""
    text = text.lower()
    text = re.sub(r"[àáạảãâầấậẩẫăằắặẳẵ]", "a", text)
    text = re.sub(r"[èéẹẻẽêềếệểễ]", "e", text)
    text = re.sub(r"[ìíịỉĩ]", "i", text)
    text = re.sub(r"[òóọỏõôồốộổỗơờớợởỡ]", "o", text)
    text = re.sub(r"[ùúụủũưừứựửữ]", "u", text)
    text = re.sub(r"[ỳýỵỷỹ]", "y", text)
    text = re.sub(r"[đ]", "d", text)
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    return text.strip("_")


class ElderlyVoiceDatasetGenerator:
    """Generator for multi-region elderly synthetic voice dataset."""

    def __init__(
        self,
        output_dir: Path | str | None = None,
        synthesizer: BaseSynthesizer | None = None,
        sample_rate: int = 48000,
    ):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DATASET_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.synthesizer = synthesizer or get_synthesizer()
        self.sample_rate = sample_rate

    def generate_benchmark_greeting(
        self,
        speaker: SpeakerProfile,
        custom_text: str | None = None,
    ) -> AudioSampleMetadata:
        """Synthesize the standard benchmark greeting for a speaker profile."""
        spk_dir = self.output_dir / speaker.folder_name
        spk_dir.mkdir(parents=True, exist_ok=True)

        text_to_speak = custom_text or speaker.prosody_text or BENCHMARK_PROMPT

        # 1. Direct neural synthesis with latent blending
        raw_audio, sr = self.synthesizer.synthesize(
            text=text_to_speak,
            voice=speaker.base_voice,
            secondary_voice=speaker.secondary_voice,
            blend_ratio=speaker.blend_ratio,
            cfg_scale=speaker.cfg_scale,
            temperature=speaker.temperature,
            target_sr=self.sample_rate,
        )

        # 2. Organic analog warmth & aging (avoids metallic phase vocoder artifacts)
        enhanced_audio = apply_analog_warmth_and_aging(
            raw_audio,
            sr=self.sample_rate,
            age=speaker.age,
        )

        # 3. File naming: <speaker_slug>_<age>t_cau_chao_gia_an.wav
        speaker_slug = slugify(speaker.name)
        file_name = f"{speaker_slug}_{speaker.age}t_cau_chao_gia_an.wav"
        file_path = spk_dir / file_name

        # 4. Save 16-bit PCM WAV
        sf.write(file_path, enhanced_audio, self.sample_rate, subtype="PCM_16")

        # 5. Extract acoustic metrics
        acoustics = analyze_audio_sample(enhanced_audio, self.sample_rate)

        # 6. Build metadata
        rel_path = file_path.relative_to(self.output_dir).as_posix()
        sample_id = f"{speaker.id}_benchmark_greeting"

        metadata = AudioSampleMetadata(
            sample_id=sample_id,
            file_name=file_name,
            relative_path=rel_path,
            absolute_path=str(file_path.resolve()),
            speaker_id=speaker.id,
            speaker_name=speaker.display_name,
            age=speaker.age,
            age_bin=speaker.age_bin,
            gender=speaker.gender.value,
            region=speaker.region.value,
            category="mau_chao_gia_an",
            utterance_text=text_to_speak,
            intent="GREETING_BENCHMARK",
            urgency="normal",
            noise_type="clean",
            snr_db=None,
            duration_sec=acoustics["duration_sec"],
            sample_rate=self.sample_rate,
            channels=1,
            f0_mean_hz=acoustics["f0_mean_hz"],
            jitter_pct=acoustics["jitter_pct"],
            shimmer_pct=acoustics["shimmer_pct"],
            hnr_db=acoustics["hnr_db"],
            source="synthetic",
            model_version="zerotts-v2.0-neural-latent-blending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return metadata

    def generate_all_benchmark(
        self,
        speakers: list[SpeakerProfile] | None = None,
        progress_callback=None,
    ) -> list[AudioSampleMetadata]:
        """Generate benchmark greeting for all configured speakers."""
        if speakers is None:
            speakers = get_speakers_config()

        manifest: list[AudioSampleMetadata] = []
        for spk in speakers:
            meta = self.generate_benchmark_greeting(speaker=spk)
            manifest.append(meta)
            if progress_callback:
                progress_callback(meta)

        # Export manifest files
        manifest_jsonl_path = self.output_dir / "manifest.jsonl"
        manifest_csv_path = self.output_dir / "metadata.csv"
        export_manifest_jsonl(manifest, manifest_jsonl_path)
        export_manifest_csv(manifest, manifest_csv_path)

        return manifest
