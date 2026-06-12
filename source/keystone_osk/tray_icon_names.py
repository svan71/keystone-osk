from __future__ import annotations

from pathlib import Path

from keystone_osk.theme import (
    DRACULA_THEME_ID,
    DUSK_THEME_ID,
    GENERIC_DARK_THEME_ID,
    GENERIC_LIGHT_THEME_ID,
    MIDNIGHT_THEME_ID,
    MOCHA_THEME_ID,
)

KEYSTONE_TRAY_ICON_NAMES = (
    "keystone-status-symbolic",
    "keystone-symbolic",
)
SYSTEM_TRAY_ICON_FALLBACK_NAMES = ("input-keyboard-symbolic",)
BUNDLED_TRAY_ICON_PATH = Path(__file__).with_name("data") / "keystone-tray-fallback.svg"


def tray_icon_theme_candidates(theme: str | None = None) -> tuple[str, ...]:
    if theme == DRACULA_THEME_ID:
        return ("keystone-status-dracula-symbolic", *KEYSTONE_TRAY_ICON_NAMES)
    if theme == MIDNIGHT_THEME_ID:
        return ("keystone-status-midnight-symbolic", "keystone-status-dracula-symbolic", *KEYSTONE_TRAY_ICON_NAMES)
    if theme == MOCHA_THEME_ID:
        return ("keystone-status-mocha-symbolic", *KEYSTONE_TRAY_ICON_NAMES)
    if theme == DUSK_THEME_ID:
        return ("keystone-status-dusk-symbolic", "keystone-status-mocha-symbolic", *KEYSTONE_TRAY_ICON_NAMES)
    if theme in {GENERIC_DARK_THEME_ID, "default-dark"}:
        return ("keystone-status-dark-symbolic", *KEYSTONE_TRAY_ICON_NAMES)
    if theme in {GENERIC_LIGHT_THEME_ID, "default-light"}:
        return ("keystone-status-light-symbolic", *KEYSTONE_TRAY_ICON_NAMES)
    return KEYSTONE_TRAY_ICON_NAMES


def tray_icon_system_fallback_candidates() -> tuple[str, ...]:
    return SYSTEM_TRAY_ICON_FALLBACK_NAMES
