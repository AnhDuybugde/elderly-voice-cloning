"""Speech synthesis and aging DSP module."""
from src.synthesis.aging_dsp import apply_presbyphonia
from src.synthesis.engine import (
    BaseSynthesizer,
    ZeroTTSSynthesizer,
    FallbackSynthesizer,
    get_synthesizer,
)

__all__ = [
    "apply_presbyphonia",
    "BaseSynthesizer",
    "ZeroTTSSynthesizer",
    "FallbackSynthesizer",
    "get_synthesizer",
]
