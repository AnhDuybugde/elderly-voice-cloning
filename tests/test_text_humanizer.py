import numpy as np

from src.core.config import get_prompts_config
from src.synthesis.text_humanizer import add_hesitations, humanize_text


def _prompt(pid):
    return next(p for c in get_prompts_config() for p in c.prompts if p.id == pid)


def test_humanizer_is_deterministic():
    p = _prompt("sh_01")
    a = humanize_text(p, "80_plus", "mien_trung", np.random.default_rng(5))
    b = humanize_text(p, "80_plus", "mien_trung", np.random.default_rng(5))
    assert a == b


def test_dialect_variants_used_and_canonical_text_kept():
    p = _prompt("sh_01")
    texts = {humanize_text(p, "50_59", "mien_trung", np.random.default_rng(s), use_hesitation=False) for s in range(20)}
    assert p.dialect_variants["mien_trung"] in texts
    assert p.text in texts  # sometimes the canonical phrasing is kept
    assert humanize_text(p, "50_59", "mien_trung", np.random.default_rng(0), use_dialect=False, use_hesitation=False) == p.text
    assert p.text == "Gia An ơi, hôm nay mấy giờ tôi phải uống thuốc huyết áp vậy?"  # label unchanged


def test_hesitation_more_frequent_when_older():
    text = "Gia An ơi, bật đèn phòng khách giúp tôi với."
    count = lambda b: sum(add_hesitations(text, b, "calm", "mien_bac", np.random.default_rng(s)) != text for s in range(200))  # noqa: E731
    assert count("80_plus") > count("50_59")


def test_urgent_tone_restarts_or_pauses():
    text = "Cứu tôi với, tôi bị ngã rồi!"
    outs = {add_hesitations(text, "80_plus", "panicked", "mien_bac", np.random.default_rng(s)) for s in range(50)}
    assert any(o.startswith("Cứu...") for o in outs)
