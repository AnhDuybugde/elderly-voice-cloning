import tempfile
from pathlib import Path
import pytest

from src.core.schema import (
    SpeakerProfile,
    GenderEnum,
    RegionEnum,
    PromptCategory,
    CategoryEnum,
    PromptItem,
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

        test_category = PromptCategory(
            id=CategoryEnum.KEU_CUU,
            display_name="Giọng nói kêu cứu",
            description="Tình huống khẩn cấp",
            prompts=[
                PromptItem(
                    id="kc_01",
                    code="keu_cuu_01_khan_cap",
                    text="Gia An ơi, cứu tôi với!",
                    intent="HELP",
                    urgency="critical",
                )
            ],
        )

        generator = ElderlyVoiceDatasetGenerator(
            output_dir=tmp_path,
            synthesizer=FallbackSynthesizer(),
            sample_rate=24000,
        )

        manifest = generator.generate_all(
            speakers=[test_speaker],
            categories=[test_category],
        )

        assert len(manifest) == 1
        meta = manifest[0]

        # Check speaker folder
        expected_folder = tmp_path / "Ong_Hai_Dang_50_tuoi_Mien_Nam" / "giong_noi_keu_cuu"
        assert expected_folder.exists()

        expected_file = expected_folder / "ong_hai_dang_50t_keu_cuu_01_khan_cap.wav"
        assert expected_file.exists()

        # Run verification tool
        assert verify_dataset(tmp_path) is True
