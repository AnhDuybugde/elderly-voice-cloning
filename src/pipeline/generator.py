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
    get_aging_params_for_age,
)
from src.core.schema import (
    SpeakerProfile,
    PromptCategory,
    AudioSampleMetadata,
)
from src.synthesis.aging_dsp import apply_presbyphonia
from src.synthesis.engine import BaseSynthesizer, get_synthesizer
from src.noise.augment import mix_audio_with_noise
from src.metrics.acoustic_features import analyze_audio_sample
from src.pipeline.manifest import (
    export_manifest_jsonl,
    export_manifest_csv,
    generate_summary_report,
)


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
        sample_rate: int = 24000,
    ):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DATASET_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.synthesizer = synthesizer or get_synthesizer()
        self.sample_rate = sample_rate

    def generate_sample(
        self,
        speaker: SpeakerProfile,
        category: PromptCategory,
        prompt_item,
        out_folder: Path,
    ) -> AudioSampleMetadata:
        """Synthesize and process a single audio sample."""
        # 1. Synthesize base speech
        raw_audio, sr = self.synthesizer.synthesize(
            text=prompt_item.text,
            voice=speaker.base_voice,
            target_sr=self.sample_rate,
        )

        # 2. Apply Presbyphonia aging DSP according to speaker age
        aging_params = get_aging_params_for_age(speaker.age_bin)
        aged_audio = apply_presbyphonia(raw_audio, sr=self.sample_rate, params=aging_params)

        # 3. Apply noise if category is 'giong_co_nhieu'
        noise_type = "clean"
        snr_db = None
        final_audio = aged_audio

        if category.id == "giong_co_nhieu":
            noise_type = prompt_item.noise_profile or "tv_background"
            snr_db = prompt_item.snr_db if prompt_item.snr_db is not None else 10.0
            final_audio = mix_audio_with_noise(
                aged_audio,
                noise_profile=noise_type,
                snr_db=snr_db,
                sr=self.sample_rate,
            )

        # 4. Generate explicit file name
        # format: <speaker_slug>_<age>t_<prompt_code>.wav
        # example: ong_hai_dang_50t_keu_cuu_01_khan_cap.wav
        speaker_slug = slugify(speaker.name)
        file_name = f"{speaker_slug}_{speaker.age}t_{prompt_item.code}.wav"
        file_path = out_folder / file_name

        # 5. Write 16-bit PCM WAV
        sf.write(file_path, final_audio, self.sample_rate, subtype="PCM_16")

        # 6. Extract acoustic metrics
        acoustics = analyze_audio_sample(final_audio, self.sample_rate)

        # 7. Build metadata
        rel_path = file_path.relative_to(self.output_dir).as_posix()
        sample_id = f"{speaker.id}_{category.id}_{prompt_item.id}"

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
            category=category.id.value,
            utterance_text=prompt_item.text,
            intent=prompt_item.intent,
            urgency=prompt_item.urgency,
            noise_type=noise_type,
            snr_db=snr_db,
            duration_sec=acoustics["duration_sec"],
            sample_rate=self.sample_rate,
            channels=1,
            f0_mean_hz=acoustics["f0_mean_hz"],
            jitter_pct=acoustics["jitter_pct"],
            shimmer_pct=acoustics["shimmer_pct"],
            hnr_db=acoustics["hnr_db"],
            source="synthetic",
            model_version="zerotts-v0.1-presbyphonia",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return metadata

    def generate_all(
        self,
        speakers: list[SpeakerProfile] | None = None,
        categories: list[PromptCategory] | None = None,
        progress_callback=None,
    ) -> list[AudioSampleMetadata]:
        """Generate complete dataset for all speakers and categories."""
        if speakers is None:
            speakers = get_speakers_config()
        if categories is None:
            categories = get_prompts_config()

        manifest: list[AudioSampleMetadata] = []

        for spk in speakers:
            # Create speaker folder: e.g. Ong_Hai_Dang_50_tuoi_Mien_Nam
            spk_dir = self.output_dir / spk.folder_name
            spk_dir.mkdir(parents=True, exist_ok=True)

            for cat in categories:
                # Create category folder: giong_noi_keu_cuu, giong_sinh_hoat, giong_co_nhieu
                cat_dir = spk_dir / cat.id.value
                cat_dir.mkdir(parents=True, exist_ok=True)

                for item in cat.prompts:
                    meta = self.generate_sample(
                        speaker=spk,
                        category=cat,
                        prompt_item=item,
                        out_folder=cat_dir,
                    )
                    manifest.append(meta)
                    if progress_callback:
                        progress_callback(meta)

        # Export manifest files
        manifest_jsonl_path = self.output_dir / "manifest.jsonl"
        manifest_csv_path = self.output_dir / "metadata.csv"
        export_manifest_jsonl(manifest, manifest_jsonl_path)
        export_manifest_csv(manifest, manifest_csv_path)

        return manifest
