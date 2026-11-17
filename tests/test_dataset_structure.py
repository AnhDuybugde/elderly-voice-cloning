import tempfile
from pathlib import Path
import pytest

from src.core.schema import (
    SpeakerProfile,
    GenderEnum,
    RegionEnum,
)
from src.synthesis.engine import FallbackSynthesizer
from src.pipeline.generator import ElderlyVoiceDatasetGenerator
from tools.verify_dataset import verify_dataset


def test_generator_structure_and_verify():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        test_speaker = SpeakerProfile(
            id="spk_test_01",
            name="Ong_Hai_Dang",
            display_name="Ông Hải Đăng",
            gender=GenderEnum.NAM,
            age=50,
            age_bin="50_59",
            region=RegionEnum.MIEN_NAM,
            region_display="Miền Nam",
            sub_region="dong_nam_bo",
            folder_name="Ong_Hai_Dang_50_tuoi_Mien_Nam",
            base_voice="huuduc",
        )

        generator = ElderlyVoiceDatasetGenerator(
            output_dir=tmp_path,
            synthesizer=FallbackSynthesizer(),
            sample_rate=48000,
        )

        manifest = generator.generate_all_benchmark(
            speakers=[test_speaker],
        )

        assert len(manifest) == 1
        meta = manifest[0]

        # Check speaker folder
        expected_folder = tmp_path / "Ong_Hai_Dang_50_tuoi_Mien_Nam"
        assert expected_folder.exists()

        expected_file = expected_folder / "ong_hai_dang_50t_cau_chao_gia_an.wav"
        assert expected_file.exists()

        # Run verification tool
        assert verify_dataset(tmp_path) is True


def test_full_generation_layout_and_manifest():
    from src.core.config import get_prompts_config
    import json

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        spk = SpeakerProfile(
            id="spk_test_02", name="Ba_Le_Thi_Mai", display_name="Bà Lê Thị Mai", gender=GenderEnum.NU,
            age=78, age_bin="70_79", region=RegionEnum.MIEN_TRUNG, region_display="Miền Trung",
            sub_region="hue", folder_name="Ba_Le_Thi_Mai_78_tuoi_Mien_Trung", base_voice="kimoanh",
            voice_mix={"kimoanh": 0.6, "baotrang": 0.4}, voice_traits={"hoarseness": 0.6},
        )
        cats = [c for c in get_prompts_config() if c.id in ("giong_noi_keu_cuu", "giong_co_nhieu")]
        cats = [c.model_copy(update={"prompts": c.prompts[:1]}) for c in cats]

        gen = ElderlyVoiceDatasetGenerator(output_dir=tmp_path, synthesizer=FallbackSynthesizer())
        manifest = gen.generate_all(speakers=[spk], categories=cats, n_variants=2, with_noise=True)

        clean = [m for m in manifest if m.noise_type == "clean"]
        noisy = [m for m in manifest if m.noise_type != "clean"]
        assert len(clean) == 1 + 2 * 2  # greeting + 2 prompts x 2 variants
        assert len(noisy) == 2          # only giong_co_nhieu has a noise profile
        f = tmp_path / "Ba_Le_Thi_Mai_78_tuoi_Mien_Trung" / "giong_noi_keu_cuu" / "ba_le_thi_mai_78t_keu_cuu_01_khan_cap_v1.wav"
        assert f.exists()
        assert (tmp_path / "manifest_noisy.jsonl").exists()

        rec = json.loads((tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[1])
        assert rec["model_version"].startswith("zerotts-v3.0")
        assert rec["dsp_params"]["tempo_scale"] > 0 and rec["voice_mix"]["kimoanh"] == 0.6
        assert rec["utterance_text"] and rec["spoken_text"]
        assert verify_dataset(tmp_path) is True
