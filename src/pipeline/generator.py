"""Dataset Generator (v3.0): neural TTS -> WORLD aging -> QC gate -> files + manifest.

Pipeline per utterance:
    1. spoken text       = prompt text (+ regional phrasing, hesitations)     text_humanizer
    2. raw speech        = ZeroTTS with a multi-voice latent mix per speaker  engine
    3. aging parameters  = age bin + speaker fingerprint + tone + take jitter voice_profile
    4. aged speech       = WORLD presbyphonia engine                          world_aging
    5. QC                = Praat metrics + ASR CER (retry with a new seed)    qc
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import soundfile as sf

from src.core.config import OUTPUT_DATASET_DIR, get_prompts_config, get_speakers_config
from src.core.schema import AudioSampleMetadata, PromptCategory, PromptItem, SpeakerProfile
from src.metrics.acoustic_features import analyze_audio_sample, count_vi_syllables, speech_activity
from src.noise.augment import mix_audio_with_noise
from src.pipeline.manifest import export_manifest_csv, export_manifest_jsonl
from src.pipeline.qc import evaluate_sample, severity
from src.synthesis.engine import BaseSynthesizer, ZeroTTSSynthesizer, get_synthesizer
from src.synthesis.text_humanizer import humanize_text
from src.synthesis.voice_profile import get_profile, resolve_aging_params, stable_seed
from src.synthesis.world_aging import age_voice

BENCHMARK_PROMPT = "Xin chào Gia An, Gia An có nghe rõ tôi nói không?"
MODEL_VERSION = "zerotts-v3.0-world-aging"
LATENT_JITTER = 0.10

# Variant recipes: v0 = canonical text (clean reference take), v1+ = humanized takes
VARIANT_RECIPES = [
    {"dialect": False, "hesitation": False, "temp_delta": 0.0},
    {"dialect": True, "hesitation": True, "temp_delta": -0.03},
    {"dialect": True, "hesitation": False, "temp_delta": 0.03},
    {"dialect": False, "hesitation": True, "temp_delta": 0.0},
]


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
    """Generator for the multi-region elderly synthetic voice dataset."""

    def __init__(
        self,
        output_dir: Path | str | None = None,
        synthesizer: BaseSynthesizer | None = None,
        sample_rate: int = 48000,
        use_asr: Optional[bool] = None,
        use_embedder: Optional[bool] = None,
        run_qc: Optional[bool] = None,
        max_attempts: int = 3,
    ):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DATASET_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.synthesizer = synthesizer or get_synthesizer()
        self.sample_rate = sample_rate

        neural = isinstance(self.synthesizer, ZeroTTSSynthesizer)
        self.use_asr = neural if use_asr is None else use_asr
        self.use_embedder = neural if use_embedder is None else use_embedder
        self.run_qc = neural if run_qc is None else run_qc
        self.max_attempts = max(1, max_attempts if self.run_qc else 1)

        self._asr = None
        self._embedder = None

    # ------------------------------------------------------------------ helpers
    @property
    def asr(self):
        if self._asr is None and self.use_asr:
            from src.metrics.intelligibility import VietnameseASR

            self._asr = VietnameseASR()
        return self._asr

    @property
    def embedder(self):
        if self._embedder is None and self.use_embedder:
            from src.metrics.speaker_similarity import SpeakerEmbedder

            self._embedder = SpeakerEmbedder()
        return self._embedder

    def render(
        self,
        speaker: SpeakerProfile,
        text: str,
        tone: Optional[str],
        seed: int,
        temp_delta: float = 0.0,
    ) -> tuple[np.ndarray, dict, dict]:
        """TTS + aging for one take. Returns (audio, dsp_params, info)."""
        gender = speaker.gender.value
        raw, sr = self.synthesizer.synthesize(
            text=text,
            voice=speaker.base_voice,
            secondary_voice=speaker.secondary_voice,
            blend_ratio=speaker.blend_ratio,
            cfg_scale=speaker.cfg_scale,
            temperature=float(np.clip(speaker.temperature + temp_delta, 0.55, 0.9)),
            target_sr=self.sample_rate,
            voice_mix=speaker.resolved_voice_mix(),
            latent_seed=stable_seed("latent", speaker.id),
            latent_jitter=LATENT_JITTER,
            seed=seed,
        )
        act = speech_activity(raw, sr)
        n_syl = count_vi_syllables(text)
        src_rate = n_syl / act["active_sec"] if act["active_sec"] > 0 and n_syl else None

        rng = np.random.default_rng(seed)
        params = resolve_aging_params(speaker, tone=tone, variant_rng=rng, source_rate_syl_s=src_rate)
        aged, info = age_voice(raw, sr, params, rng=rng, gender=gender, return_info=True)
        info["src_rate_syl_s"] = round(src_rate or 0.0, 3)
        return aged, params.to_dict(), info

    def _measure(self, audio: np.ndarray, speaker: SpeakerProfile, spoken_text: str) -> tuple[dict, Optional[float]]:
        metrics = analyze_audio_sample(audio, self.sample_rate, gender=speaker.gender.value, text=spoken_text)
        cer_val = None
        if self.asr is not None:
            from src.metrics.intelligibility import cer

            metrics["asr_text"] = self.asr.transcribe(audio, self.sample_rate)
            cer_val = round(cer(spoken_text, metrics["asr_text"]), 4)
        return metrics, cer_val

    def produce(
        self,
        speaker: SpeakerProfile,
        spoken_text: str,
        tone: Optional[str],
        base_seed: int,
        temp_delta: float = 0.0,
    ) -> dict:
        """Render with QC retries; keep the first passing take, else the least-bad one."""
        qc_ranges = get_profile(speaker.gender.value, speaker.age_bin)["qc"]
        n_syl = count_vi_syllables(spoken_text)
        best = None
        for attempt in range(self.max_attempts):
            seed = (base_seed + 7919 * attempt) % (2**31)
            audio, params, info = self.render(speaker, spoken_text, tone, seed, temp_delta)
            metrics, cer_val = self._measure(audio, speaker, spoken_text)
            if self.run_qc:
                ok, reasons = evaluate_sample(metrics, qc_ranges, n_syl, cer_val)
            else:
                ok, reasons = None, []
            cand = {
                "audio": audio, "params": params, "info": info, "metrics": metrics, "cer": cer_val,
                "qc_pass": ok, "qc_reasons": reasons, "seed": seed, "attempts": attempt + 1,
            }
            if best is None or severity(reasons) < severity(best["qc_reasons"]):
                best = cand
            if ok or not self.run_qc:
                break
        best["attempts"] = attempt + 1
        return best

    def _build_metadata(
        self,
        speaker: SpeakerProfile,
        result: dict,
        file_path: Path,
        root: Path,
        category: str,
        utterance_text: str,
        spoken_text: str,
        intent: str,
        urgency: str,
        tone: Optional[str],
        variant_id: int,
        noise_type: str = "clean",
        snr_db: Optional[float] = None,
        metrics_override: Optional[dict] = None,
    ) -> AudioSampleMetadata:
        m = metrics_override or result["metrics"]
        rel = file_path.relative_to(root).as_posix()
        stem = file_path.stem
        return AudioSampleMetadata(
            sample_id=f"{speaker.id}__{stem}",
            file_name=file_path.name,
            relative_path=rel,
            absolute_path=str(file_path.resolve()),
            speaker_id=speaker.id,
            speaker_name=speaker.display_name,
            age=speaker.age,
            age_bin=speaker.age_bin,
            gender=speaker.gender.value,
            region=speaker.region.value,
            category=category,
            utterance_text=utterance_text,
            intent=intent,
            urgency=urgency,
            noise_type=noise_type,
            snr_db=snr_db,
            duration_sec=m["duration_sec"],
            sample_rate=self.sample_rate,
            channels=1,
            f0_mean_hz=m["f0_mean_hz"],
            jitter_pct=m["jitter_pct"],
            shimmer_pct=m["shimmer_pct"],
            hnr_db=m["hnr_db"],
            source="synthetic",
            model_version=MODEL_VERSION,
            created_at=datetime.now(timezone.utc).isoformat(),
            variant_id=variant_id,
            seed=result["seed"],
            spoken_text=spoken_text,
            tone=tone,
            voice_mix=speaker.resolved_voice_mix(),
            dsp_params={**result["params"], **{k: v for k, v in result["info"].items()}},
            f0_std_hz=m["f0_std_hz"],
            cpps_db=m["cpps_db"],
            speech_rate_syl_s=m["speech_rate_syl_s"],
            pause_ratio=m["pause_ratio"],
            cer=result["cer"],
            asr_text=result["metrics"].get("asr_text"),
            qc_pass=result["qc_pass"],
            qc_reasons=result["qc_reasons"] or None,
            attempts=result["attempts"],
        )

    # ---------------------------------------------------------------- public API
    def generate_benchmark_greeting(
        self,
        speaker: SpeakerProfile,
        custom_text: str | None = None,
    ) -> AudioSampleMetadata:
        """Synthesize the standard benchmark greeting for a speaker profile."""
        spk_dir = self.output_dir / speaker.folder_name
        spk_dir.mkdir(parents=True, exist_ok=True)
        text = custom_text or speaker.prosody_text or BENCHMARK_PROMPT

        result = self.produce(speaker, text, tone="calm", base_seed=stable_seed(speaker.id, "benchmark"))
        file_path = spk_dir / f"{slugify(speaker.name)}_{speaker.age}t_cau_chao_gia_an.wav"
        sf.write(file_path, result["audio"], self.sample_rate, subtype="PCM_16")
        self._last_audio = result["audio"]

        return self._build_metadata(
            speaker, result, file_path, self.output_dir, "mau_chao_gia_an",
            BENCHMARK_PROMPT, text, "GREETING_BENCHMARK", "normal", "calm", 0,
        )

    def generate_utterance(
        self,
        speaker: SpeakerProfile,
        category: PromptCategory,
        prompt: PromptItem,
        variant_id: int = 0,
        with_noise: bool = False,
    ) -> list[AudioSampleMetadata]:
        recipe = VARIANT_RECIPES[variant_id % len(VARIANT_RECIPES)]
        base_seed = stable_seed(speaker.id, prompt.id, variant_id)
        text_rng = np.random.default_rng(base_seed)
        spoken = humanize_text(
            prompt, speaker.age_bin, speaker.region.value, text_rng,
            use_dialect=recipe["dialect"], use_hesitation=recipe["hesitation"],
        )

        result = self.produce(speaker, spoken, prompt.tone, base_seed, recipe["temp_delta"])

        out_dir = self.output_dir / speaker.folder_name / category.id
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{slugify(speaker.name)}_{speaker.age}t_{prompt.code}_v{variant_id}"
        file_path = out_dir / f"{stem}.wav"
        sf.write(file_path, result["audio"], self.sample_rate, subtype="PCM_16")
        self._last_audio = result["audio"]

        records = [
            self._build_metadata(
                speaker, result, file_path, self.output_dir, category.id, prompt.text, spoken,
                prompt.intent, prompt.urgency, prompt.tone, variant_id,
            )
        ]

        if with_noise and prompt.noise_profile:
            noisy_root = self.output_dir / "_noisy"
            noisy_dir = noisy_root / speaker.folder_name / category.id
            noisy_dir.mkdir(parents=True, exist_ok=True)
            np.random.seed(base_seed % (2**32))
            noisy = mix_audio_with_noise(result["audio"], prompt.noise_profile, prompt.snr_db or 10.0, self.sample_rate)
            noisy_path = noisy_dir / f"{stem}_{prompt.noise_profile}_snr{int(prompt.snr_db or 10)}.wav"
            sf.write(noisy_path, noisy, self.sample_rate, subtype="PCM_16")
            noisy_metrics = analyze_audio_sample(noisy, self.sample_rate, speaker.gender.value, spoken)
            records.append(
                self._build_metadata(
                    speaker, result, noisy_path, self.output_dir, category.id, prompt.text, spoken,
                    prompt.intent, prompt.urgency, prompt.tone, variant_id,
                    noise_type=prompt.noise_profile, snr_db=prompt.snr_db, metrics_override=noisy_metrics,
                )
            )
        return records

    def generate_all_benchmark(
        self,
        speakers: list[SpeakerProfile] | None = None,
        progress_callback: Optional[Callable] = None,
    ) -> list[AudioSampleMetadata]:
        """Generate the benchmark greeting for all configured speakers."""
        speakers = speakers if speakers is not None else get_speakers_config()
        manifest: list[AudioSampleMetadata] = []
        audio_by_sample: dict[str, np.ndarray] = {}
        for spk in speakers:
            meta = self.generate_benchmark_greeting(speaker=spk)
            manifest.append(meta)
            audio_by_sample[meta.sample_id] = self._last_audio
            if progress_callback:
                progress_callback(meta)
        self._finalize(manifest, audio_by_sample)
        return manifest

    def generate_all(
        self,
        speakers: list[SpeakerProfile] | None = None,
        categories: list[PromptCategory] | None = None,
        n_variants: int = 3,
        with_noise: bool = False,
        include_benchmark: bool = True,
        progress_callback: Optional[Callable] = None,
    ) -> list[AudioSampleMetadata]:
        """Full matrix: speakers x prompts x variants (+ benchmark greeting)."""
        speakers = speakers if speakers is not None else get_speakers_config()
        categories = categories if categories is not None else get_prompts_config()
        manifest: list[AudioSampleMetadata] = []
        audio_by_sample: dict[str, np.ndarray] = {}

        for spk in speakers:
            if include_benchmark:
                meta = self.generate_benchmark_greeting(spk)
                manifest.append(meta)
                audio_by_sample[meta.sample_id] = self._last_audio
                if progress_callback:
                    progress_callback(meta)
            for cat in categories:
                for prompt in cat.prompts:
                    for v in range(n_variants):
                        recs = self.generate_utterance(spk, cat, prompt, v, with_noise=with_noise)
                        audio_by_sample[recs[0].sample_id] = self._last_audio
                        manifest.extend(recs)
                        if progress_callback:
                            for r in recs:
                                progress_callback(r)

        self._finalize(manifest, audio_by_sample)
        return manifest

    generate_full_dataset = generate_all

    # ------------------------------------------------------------ finalization
    def _finalize(self, manifest: list[AudioSampleMetadata], audio_by_sample: dict[str, np.ndarray]) -> None:
        if self.embedder is not None and audio_by_sample:
            self._speaker_identity_report(manifest, audio_by_sample)
        clean = [m for m in manifest if m.noise_type == "clean"]
        noisy = [m for m in manifest if m.noise_type != "clean"]
        clean = self._merge_existing(clean, self.output_dir / "manifest.jsonl")
        export_manifest_jsonl(clean, self.output_dir / "manifest.jsonl")
        export_manifest_csv(clean, self.output_dir / "metadata.csv")
        if noisy or (self.output_dir / "manifest_noisy.jsonl").exists():
            noisy = self._merge_existing(noisy, self.output_dir / "manifest_noisy.jsonl")
            export_manifest_jsonl(noisy, self.output_dir / "manifest_noisy.jsonl")
            export_manifest_csv(noisy, self.output_dir / "metadata_noisy.csv")

    def _merge_existing(self, new_records: list[AudioSampleMetadata], path: Path) -> list[AudioSampleMetadata]:
        """Keep earlier records (other speakers / prompts) whose files still exist; new ones win."""
        if not path.exists():
            return new_records
        fresh = {m.relative_path for m in new_records}
        kept = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = AudioSampleMetadata(**json.loads(line))
            except Exception:
                continue
            if rec.relative_path not in fresh and (self.output_dir / rec.relative_path).exists():
                kept.append(rec)
        return kept + new_records

    def _speaker_identity_report(self, manifest, audio_by_sample) -> None:
        from src.metrics.speaker_similarity import centroid, cosine, pairwise_similarity

        embs = {sid: self.embedder.embed(a, self.sample_rate) for sid, a in audio_by_sample.items()}
        by_spk: dict[str, list] = {}
        for m in manifest:
            if m.sample_id in embs:
                by_spk.setdefault(m.speaker_id, []).append(embs[m.sample_id])
        cents = {spk: centroid(v) for spk, v in by_spk.items()}
        for m in manifest:
            if m.sample_id in embs:
                m.speaker_sim_to_centroid = round(cosine(embs[m.sample_id], cents[m.speaker_id]), 4)

        names, mat = pairwise_similarity(cents)
        report_dir = self.output_dir / "reports"
        report_dir.mkdir(exist_ok=True)
        with open(report_dir / "speaker_similarity.json", "w", encoding="utf-8") as f:
            json.dump({"speakers": names, "matrix": np.round(mat, 4).tolist()}, f, ensure_ascii=False, indent=1)
