# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

ACCENT_VARIANTS: dict[str, tuple[str, ...]] = {
    "a": ("à", "á", "â", "ä", "ã", "å"),
    "e": ("è", "é", "ê", "ë"),
    "i": ("ì", "í", "î", "ï"),
    "o": ("ò", "ó", "ô", "ö", "õ"),
    "u": ("ù", "ú", "û", "ü"),
    "n": ("ñ",),
    "c": ("ç",),
    "y": ("ý", "ÿ"),
}


def has_accents(letter: str) -> bool:
    if len(letter) != 1:
        return False
    return letter.lower() in ACCENT_VARIANTS


def accent_variants_for(letter: str, uppercase: bool) -> tuple[str, ...]:
    base = letter.lower()
    variants = ACCENT_VARIANTS.get(base, ())
    if uppercase:
        return tuple(v.upper() for v in variants)
    return variants
