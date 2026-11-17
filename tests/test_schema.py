import pytest
from src.core.config import get_speakers_config, get_prompts_config, get_aging_params_for_age
from src.core.schema import GenderEnum, RegionEnum


def test_speakers_config():
    speakers = get_speakers_config()
    assert len(speakers) >= 3

    # Check Ong Hai Dang 50 tuoi
    hai_dang = next((s for s in speakers if s.name == "Ong_Hai_Dang"), None)
    assert hai_dang is not None
    assert hai_dang.age == 50
    assert hai_dang.gender == GenderEnum.NAM
    assert hai_dang.region == RegionEnum.MIEN_NAM
    assert "Ong_Hai_Dang_50_tuoi" in hai_dang.folder_name


def test_prompts_config():
    categories = get_prompts_config()
    cat_ids = [c.id for c in categories]
    assert "giong_noi_keu_cuu" in cat_ids
    assert "giong_sinh_hoat" in cat_ids
    assert "giong_co_nhieu" in cat_ids

    for c in categories:
        assert len(c.prompts) > 0


def test_aging_params():
    params_50 = get_aging_params_for_age("50_59")
    params_80 = get_aging_params_for_age("80_plus")

    # 80+ should have slower tempo and higher tremor/jitter than 50-59
    assert params_80.tempo_scale < params_50.tempo_scale
    assert params_80.tremor_depth > params_50.tremor_depth
    assert params_80.jitter_factor > params_50.jitter_factor
