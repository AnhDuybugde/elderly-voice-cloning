"""Text-level humanization for elderly speech.

Older speakers hesitate, restart words and use regional particles. The TTS reads
what it is given, so we shape the *spoken* text (stored as `spoken_text`) while
the canonical `utterance_text` (the intent label) stays unchanged.

All choices are driven by a seeded RNG -> reproducible variants.
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np

from src.core.schema import PromptItem

# Probability that a take contains a hesitation, by age bin
HESITATION_PROB = {"50_59": 0.15, "60_69": 0.25, "70_79": 0.40, "80_plus": 0.55}
URGENT_TONES = {"panicked", "urgent", "in_pain", "strained", "breathless"}
FILLERS_BY_REGION = {
    "mien_bac": ["ờ", "à"],
    "mien_trung": ["ờ", "à"],
    "mien_nam": ["ờ", "à", "ừm"],
}


def pick_base_text(prompt: PromptItem, region: str, rng: np.random.Generator, use_dialect: bool) -> str:
    """Canonical text or (with probability 0.7 when enabled) the regional phrasing."""
    variants = prompt.dialect_variants or {}
    if use_dialect and region in variants and rng.random() < 0.7:
        return variants[region]
    return prompt.text


def _first_clause_break(text: str) -> Optional[int]:
    m = re.search(r"[,?]", text)
    return m.end() if m else None


def add_hesitations(text: str, age_bin: str, tone: Optional[str], region: str, rng: np.random.Generator) -> str:
    """Insert pauses ("..."), fillers or a word restart, depending on age and tone."""
    if rng.random() > HESITATION_PROB.get(age_bin, 0.25):
        return text

    words = text.split()
    if len(words) < 3:
        return text

    if tone in URGENT_TONES:
        # Urgent speech: restart the first word ("Cứu... cứu tôi với") or break after the call
        if rng.random() < 0.5:
            first = words[0].rstrip(",.!?")
            return f"{first}... {text[0].lower() + text[1:]}"
        brk = _first_clause_break(text)
        if brk:
            return text[:brk].rstrip(",") + "..." + text[brk:]
        return text

    choice = rng.random()
    brk = _first_clause_break(text)
    if choice < 0.45 and brk:
        # Long pause after the vocative / first clause
        return text[:brk].rstrip(",") + "..." + text[brk:]
    if choice < 0.8:
        # Filler at a clause boundary (or sentence start)
        filler = rng.choice(FILLERS_BY_REGION.get(region, ["ờ"]))
        if brk:
            return text[:brk] + f" {filler}..." + text[brk:]
        return f"{filler.capitalize()}... {text[0].lower() + text[1:]}"
    # Mid-sentence pause before the last few words
    cut = int(rng.integers(max(2, len(words) // 2), len(words) - 1))
    return " ".join(words[:cut]) + "... " + " ".join(words[cut:])


def humanize_text(
    prompt: PromptItem,
    age_bin: str,
    region: str,
    rng: np.random.Generator,
    use_dialect: bool = True,
    use_hesitation: bool = True,
) -> str:
    text = pick_base_text(prompt, region, rng, use_dialect)
    if use_hesitation and "..." not in text:
        text = add_hesitations(text, age_bin, prompt.tone, region, rng)
    return text
