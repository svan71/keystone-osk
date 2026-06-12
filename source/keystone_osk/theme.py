from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace as _dc_replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from keystone_osk.config import system_theme_dir, user_theme_dir

THEME_PACK_SCHEMA_VERSION = 1
GENERIC_DARK_THEME_ID = "dark"
GENERIC_LIGHT_THEME_ID = "light"
DRACULA_THEME_ID = "dracula"
MIDNIGHT_THEME_ID = "midnight"
MOCHA_THEME_ID = "mocha"
DUSK_THEME_ID = "dusk"
BUILTIN_THEME_IDS = (
    DRACULA_THEME_ID,
    MIDNIGHT_THEME_ID,
    MOCHA_THEME_ID,
    DUSK_THEME_ID,
    GENERIC_DARK_THEME_ID,
    GENERIC_LIGHT_THEME_ID,
)
THEME_ALIASES = {
    "default-dark": GENERIC_DARK_THEME_ID,
    "default-light": GENERIC_LIGHT_THEME_ID,
}
THEME_LABELS = {
    DRACULA_THEME_ID: "Dracula",
    MIDNIGHT_THEME_ID: "Midnight",
    MOCHA_THEME_ID: "Mocha",
    DUSK_THEME_ID: "Dusk",
    GENERIC_DARK_THEME_ID: "Dark",
    GENERIC_LIGHT_THEME_ID: "Light",
}
def first_run_theme_id(color_scheme: str | None) -> str:
    """Pick the out-of-the-box theme for a fresh install from the desktop's
    light/dark preference. Anything but an explicit "light" preference uses the
    generic dark theme (the safe neutral default when there is no signal)."""
    if color_scheme == "light":
        return GENERIC_LIGHT_THEME_ID
    return GENERIC_DARK_THEME_ID


THEME_PACK_SAFE_SECTIONS = frozenset(
    {
        "schema_version",
        "id",
        "name",
        "inherits",
        "colors",
        "icons",
        "font",
        "spacing",
        "corner_radius",
        "border_width",
        # validate_theme_pack range-checks a top-level "opacity", so it must be
        # an accepted section too — otherwise a pack using it is rejected as
        # "unsupported section: opacity" before its value is ever checked.
        "opacity",
    }
)
THEME_PACK_FORBIDDEN_SECTIONS = frozenset(
    {
        "backend",
        "ydotool",
        "ydotool_command",
        "window_flags",
        "key_output_mapping",
        "subprocess",
        "python",
        "code",
    }
)
THEME_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")
METRIC_LIMITS = {
    "font.size": (8, 28),
    "spacing.key_gap": (2, 20),
    "corner_radius.*": (0, 24),
    "border_width.*": (0, 4),
    "opacity": (0.5, 1.0),
}


@dataclass(frozen=True)
class ThemePalette:
    panel_top: str
    panel_bottom: str
    panel_border: str
    text: str
    key_normal_top: str
    key_normal_bottom: str
    key_normal_border: str
    key_hover_top: str
    key_hover_bottom: str
    key_hover_border: str
    key_locked_top: str
    key_locked_bottom: str
    key_locked_border: str
    control_background: str
    control_border: str
    suggestion_background: str
    suggestion_border: str
    menu_background: str
    menu_selected_background: str
    restore_icon_foreground: str
    restore_icon_background: tuple[int, int, int, int]


@dataclass(frozen=True)
class KeyPaintStyle:
    top_color: str
    bottom_color: str
    border_color: str
    border_width: int


@dataclass(frozen=True)
class ThemePackDetails:
    theme_id: str
    name: str
    path: Path | None
    status: str
    inherits: str


THEMES = {
    DRACULA_THEME_ID: ThemePalette(
        panel_top="#282a36",
        panel_bottom="#282a36",
        panel_border="#f8f8f2",
        text="#f8f8f2",
        key_normal_top="#2b2d39",
        key_normal_bottom="#282a36",
        key_normal_border="#5f4b78",
        key_hover_top="#343746",
        key_hover_bottom="#2b2d39",
        key_hover_border="#f8f8f2",
        key_locked_top="#44475a",
        key_locked_bottom="#343746",
        key_locked_border="#bd93f9",
        control_background="#282a36",
        control_border="#6a5487",
        suggestion_background="#44475a",
        suggestion_border="#f8f8f2",
        menu_background="#282a36",
        menu_selected_background="#44475a",
        restore_icon_foreground="#bd93f9",
        restore_icon_background=(40, 42, 54, 179),
    ),
    MIDNIGHT_THEME_ID: ThemePalette(
        panel_top="#1e1f29",
        panel_bottom="#111217",
        panel_border="#f8f8f2",
        text="#f8f8f2",
        key_normal_top="#21222c",
        key_normal_bottom="#15161d",
        key_normal_border="#343746",
        key_hover_top="#2a2d3a",
        key_hover_bottom="#191a21",
        key_hover_border="#f8f8f2",
        key_locked_top="#343746",
        key_locked_bottom="#21222c",
        key_locked_border="#bd93f9",
        control_background="#21222c",
        control_border="#44475a",
        suggestion_background="#2a2d3a",
        suggestion_border="#f8f8f2",
        menu_background="#21222c",
        menu_selected_background="#343746",
        restore_icon_foreground="#44475a",
        restore_icon_background=(23, 25, 35, 153),
    ),
    MOCHA_THEME_ID: ThemePalette(
        panel_top="#1e1e2e",
        panel_bottom="#1e1e2e",
        panel_border="#cdd6f4",
        text="#cdd6f4",
        key_normal_top="#202032",
        key_normal_bottom="#1e1e2e",
        key_normal_border="#6f5a88",
        key_hover_top="#313244",
        key_hover_bottom="#202032",
        key_hover_border="#cdd6f4",
        key_locked_top="#313244",
        key_locked_bottom="#1e1e2e",
        key_locked_border="#cba6f7",
        control_background="#1e1e2e",
        control_border="#7b6398",
        suggestion_background="#313244",
        suggestion_border="#cdd6f4",
        menu_background="#1e1e2e",
        menu_selected_background="#313244",
        restore_icon_foreground="#cba6f7",
        restore_icon_background=(30, 30, 46, 179),
    ),
    DUSK_THEME_ID: ThemePalette(
        panel_top="#1e1e2e",
        panel_bottom="#11111b",
        panel_border="#cdd6f4",
        text="#cdd6f4",
        key_normal_top="#313244",
        key_normal_bottom="#181825",
        key_normal_border="#45475a",
        key_hover_top="#45475a",
        key_hover_bottom="#1e1e2e",
        key_hover_border="#cdd6f4",
        key_locked_top="#45475a",
        key_locked_bottom="#313244",
        key_locked_border="#89b4fa",
        control_background="#313244",
        control_border="#585b70",
        suggestion_background="#45475a",
        suggestion_border="#cdd6f4",
        menu_background="#313244",
        menu_selected_background="#45475a",
        restore_icon_foreground="#cdd6f4",
        restore_icon_background=(30, 30, 46, 179),
    ),
    GENERIC_DARK_THEME_ID: ThemePalette(
        panel_top="#050505",
        panel_bottom="#000000",
        panel_border="#ffffff",
        text="#ffffff",
        key_normal_top="#0f1012",
        key_normal_bottom="#030304",
        key_normal_border="#737982",
        key_hover_top="#181a1e",
        key_hover_bottom="#07080a",
        key_hover_border="#ffffff",
        key_locked_top="#202329",
        key_locked_bottom="#0d0f12",
        key_locked_border="#ffffff",
        control_background="#0d0e10",
        control_border="#7b828b",
        suggestion_background="#111317",
        suggestion_border="#ffffff",
        menu_background="#0d0e10",
        menu_selected_background="#16181d",
        restore_icon_foreground="#ffffff",
        restore_icon_background=(0, 0, 0, 190),
    ),
    GENERIC_LIGHT_THEME_ID: ThemePalette(
        panel_top="#ffffff",
        panel_bottom="#eeeeee",
        panel_border="#000000",
        text="#000000",
        key_normal_top="#ffffff",
        key_normal_bottom="#f2f2f2",
        key_normal_border="#999999",
        key_hover_top="#f6f6f6",
        key_hover_bottom="#e6e6e6",
        key_hover_border="#000000",
        key_locked_top="#e8e8e8",
        key_locked_bottom="#d8d8d8",
        key_locked_border="#000000",
        control_background="#ffffff",
        control_border="#777777",
        suggestion_background="#ffffff",
        suggestion_border="#000000",
        menu_background="#ffffff",
        menu_selected_background="#e9e9e9",
        restore_icon_foreground="#000000",
        restore_icon_background=(255, 255, 255, 210),
    ),
}


@dataclass(frozen=True)
class ResolvedTheme:
    id: str
    source: str            # "builtin" | "system" | "user"
    palette: ThemePalette
    opacity: float = 1.0
    font: dict = field(default_factory=dict)
    spacing: dict = field(default_factory=dict)
    corner_radius: dict = field(default_factory=dict)
    border_width: dict = field(default_factory=dict)
    icons: dict = field(default_factory=dict)


def normalized_theme_name(theme: str | None) -> str:
    if theme is None:
        return DRACULA_THEME_ID
    value = str(theme).strip().lower()
    if value in THEMES:
        return value
    return THEME_ALIASES.get(value, DRACULA_THEME_ID)


def normalized_theme_pack_reference(theme: str) -> str:
    value = str(theme).strip().lower()
    return THEME_ALIASES.get(value, value)


def normalize_theme_id(raw: str | None) -> str:
    """Sanitize/normalize an ID string only (alias-resolve, lowercase, strip). No validity judgement."""
    if raw is None:
        return DRACULA_THEME_ID
    value = str(raw).strip().lower()
    return THEME_ALIASES.get(value, value)


def resolve_theme_id(raw: str | None, discovered_themes: tuple[str, ...], *, strict: bool) -> str | None:
    """Resolve to a valid theme id among discovered_themes.
    strict=True: return None if not found (caller errors, no fallback, no persist).
    strict=False: return a safe builtin fallback for stored/startup values."""
    candidate = normalize_theme_id(raw)
    if candidate in discovered_themes:
        return candidate
    return None if strict else DRACULA_THEME_ID


def theme_label(theme: str | None = None) -> str:
    return THEME_LABELS[normalized_theme_name(theme)]


def theme_display_label(theme: str | None = None, environ: dict[str, str] | None = None) -> str:
    theme_id = normalize_theme_id(theme)
    if theme_id in THEME_LABELS:
        return THEME_LABELS[theme_id]
    details = theme_pack_details(theme_id, environ)
    if details.status == "valid":
        return details.name
    return THEME_LABELS[DRACULA_THEME_ID]


def theme_menu_choices(environ: dict[str, str] | None = None) -> tuple[tuple[str, str], ...]:
    choices: list[tuple[str, str]] = sorted(
        ((tid, THEME_LABELS[tid]) for tid in BUILTIN_THEME_IDS),
        key=lambda choice: choice[1].lower(),
    )
    seen = set(BUILTIN_THEME_IDS)
    extras: list[tuple[str, str]] = []
    for theme_id in discover_theme_pack_ids(environ):
        if theme_id in seen:
            continue
        seen.add(theme_id)
        details = theme_pack_details(theme_id, environ)
        if details.status == "valid":
            extras.append((theme_id, details.name))
    extras.sort(key=lambda choice: choice[1].lower())
    return tuple(choices) + tuple(extras)


def bundled_theme_dir() -> Path:
    return Path(__file__).with_name("themes")


def default_theme_pack_id(theme: str | None = None) -> str:
    return normalized_theme_name(theme)


def theme_pack_search_dirs(environ: dict[str, str] | None = None) -> tuple[Path, ...]:
    return (user_theme_dir(environ), system_theme_dir(), bundled_theme_dir())


def theme_pack_path(theme_id: str, environ: dict[str, str] | None = None) -> Path | None:
    normalized_theme_id = normalized_theme_pack_reference(theme_id)
    # Built-in ids are reserved: they resolve only to the bundled pack, so a
    # user/system pack sharing the name can never shadow what "dracula" means.
    if normalized_theme_id in BUILTIN_THEME_IDS:
        bundled = bundled_theme_dir() / normalized_theme_id / "theme.json"
        return bundled if bundled.exists() else None
    for theme_dir in theme_pack_search_dirs(environ):
        candidate = theme_dir / normalized_theme_id / "theme.json"
        if candidate.exists():
            return candidate
    return None


def discover_theme_pack_ids(environ: dict[str, str] | None = None) -> tuple[str, ...]:
    theme_ids = list(BUILTIN_THEME_IDS)
    for theme_dir in theme_pack_search_dirs(environ):
        try:
            children = sorted(theme_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if child.name not in theme_ids and (child / "theme.json").exists():
                theme_ids.append(child.name)
    return tuple(theme_ids)


def discover_valid_theme_ids(environ: dict[str, str] | None = None) -> tuple[str, ...]:
    """Like discover_theme_pack_ids() but filters out user/system packs whose status is not 'valid'.
    Builtins are always included (they are always valid). Use this for strict theme resolution."""
    theme_ids: list[str] = list(BUILTIN_THEME_IDS)
    seen = set(BUILTIN_THEME_IDS)
    for theme_id in discover_theme_pack_ids(environ):
        if theme_id in seen:
            continue
        seen.add(theme_id)
        if theme_pack_details(theme_id, environ).status == "valid":
            theme_ids.append(theme_id)
    return tuple(theme_ids)


def _is_safe_relative_icon_path(path_value: str, theme_dir: Path | None = None) -> bool:
    icon_path = Path(path_value)
    if icon_path.is_absolute() or ".." in icon_path.parts:
        return False
    if theme_dir is None:
        return True
    try:
        (theme_dir / icon_path).resolve().relative_to(theme_dir.resolve())
    except ValueError:
        return False
    return True


def _metric_in_range(value: Any, minimum: float, maximum: float) -> bool:
    return isinstance(value, (int, float)) and minimum <= value <= maximum


def validate_theme_pack(
    data: Any,
    *,
    theme_dir: Path | None = None,
    available_theme_ids: tuple[str, ...] = BUILTIN_THEME_IDS,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ("theme pack must be an object",)
    keys = set(data)
    for key in sorted(keys - THEME_PACK_SAFE_SECTIONS):
        errors.append(f"unsupported section: {key}")
    for key in sorted(keys & THEME_PACK_FORBIDDEN_SECTIONS):
        errors.append(f"forbidden section: {key}")
    if data.get("schema_version") != THEME_PACK_SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    theme_id = data.get("id")
    if not isinstance(theme_id, str) or not THEME_ID_PATTERN.fullmatch(theme_id):
        errors.append("unsafe theme id")
    inherits = data.get("inherits")
    if inherits is not None and (
        not isinstance(inherits, str) or inherits == theme_id or normalized_theme_pack_reference(inherits) not in available_theme_ids
    ):
        errors.append("invalid inherits")
    colors = data.get("colors", {})
    if not isinstance(colors, dict):
        errors.append("colors must be an object")
    else:
        for key, value in colors.items():
            if not isinstance(key, str) or not isinstance(value, str) or not HEX_COLOR_PATTERN.fullmatch(value):
                errors.append(f"invalid color: {key}")
    icons = data.get("icons", {})
    if not isinstance(icons, dict):
        errors.append("icons must be an object")
    else:
        for key, value in icons.items():
            if not isinstance(key, str) or not isinstance(value, str) or not _is_safe_relative_icon_path(value, theme_dir):
                errors.append(f"invalid icon path: {key}")
    font = data.get("font", {})
    if not isinstance(font, dict):
        errors.append("font must be an object")
    else:
        if "size" in font and not _metric_in_range(font["size"], *METRIC_LIMITS["font.size"]):
            errors.append("font.size out of range")
        if "family" in font and not isinstance(font["family"], str):
            errors.append("font.family must be text")
    spacing = data.get("spacing", {})
    if not isinstance(spacing, dict):
        errors.append("spacing must be an object")
    else:
        if "key_gap" in spacing and not _metric_in_range(spacing["key_gap"], *METRIC_LIMITS["spacing.key_gap"]):
            errors.append("spacing.key_gap out of range")
    for section_name, limit_key in (("corner_radius", "corner_radius.*"), ("border_width", "border_width.*")):
        section = data.get(section_name, {})
        if not isinstance(section, dict):
            errors.append(f"{section_name} must be an object")
            continue
        for key, value in section.items():
            if not isinstance(key, str) or not _metric_in_range(value, *METRIC_LIMITS[limit_key]):
                errors.append(f"{section_name}.{key} out of range")
    if "opacity" in data and not _metric_in_range(data["opacity"], *METRIC_LIMITS["opacity"]):
        errors.append("opacity out of range")
    return tuple(errors)


def _raw_inherits(theme_id: str, environ: dict[str, str] | None = None) -> str:
    """Read only the 'inherits' field from a pack's theme.json without full validation."""
    path = theme_pack_path(theme_id, environ)
    if path is None:
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    inherits = data.get("inherits")
    return str(inherits).strip().lower() if isinstance(inherits, str) else ""


def inheritance_cycle(theme_id: str, environ: dict[str, str] | None = None) -> bool:
    seen: set[str] = set()
    current = normalize_theme_id(theme_id)
    while current and current not in BUILTIN_THEME_IDS:
        if current in seen:
            return True
        seen.add(current)
        inherits = _raw_inherits(current, environ)
        if not inherits:
            return False  # missing/invalid pack or no inherits ends the chain
        current = normalize_theme_id(inherits)
    return False


def load_theme_pack(theme_id: str, environ: dict[str, str] | None = None) -> dict[str, Any]:
    # Gate on the full validity verdict, not just the pack's own schema: a pack
    # that inherits an invalid/missing parent, or sits in an inheritance cycle,
    # must collapse to {} here too. validate_theme_pack() (used by the unchecked
    # loader and by theme_pack_details) only confirms the parent *exists*, not
    # that it is valid, so a direct load_theme_pack() call would otherwise still
    # return data for an inherited-invalid pack. theme_pack_details() reads JSON
    # itself and never calls back into load_theme_pack, so there is no recursion.
    if theme_pack_details(theme_id, environ).status != "valid":
        return {}
    return _load_theme_pack_unchecked(theme_id, environ)


def _load_theme_pack_unchecked(theme_id: str, environ: dict[str, str] | None = None) -> dict[str, Any]:
    path = theme_pack_path(theme_id, environ)
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if validate_theme_pack(data, theme_dir=path.parent, available_theme_ids=discover_theme_pack_ids(environ)):
        return {}
    return data


# Note: load_theme_pack intentionally collapses "missing", "malformed", and any
# "invalid" (including inherited-invalid / cyclic) to {} so callers can merge it
# unconditionally. The missing-vs-invalid distinction (and the first validation
# error) is reported by theme_pack_details() instead.


def _inherited_packs_valid(theme_id: str, environ: dict[str, str] | None = None) -> bool:
    """A pack may inherit only from a builtin or a fully-valid system/user pack.
    Raw discovery makes a parent *exist*; it does not make it valid. Recurses up
    the chain via theme_pack_details, which short-circuits cycles before reaching
    this check, so a cyclic chain cannot loop here."""
    inherits = _raw_inherits(normalize_theme_id(theme_id), environ)
    if not inherits:
        return True
    parent = normalize_theme_id(inherits)
    if parent in BUILTIN_THEME_IDS:
        return True
    return theme_pack_details(parent, environ).status == "valid"


def theme_pack_details(theme_id: str, environ: dict[str, str] | None = None) -> ThemePackDetails:
    normalized_theme_id = normalized_theme_pack_reference(theme_id)
    label = THEME_LABELS.get(normalized_theme_id, normalized_theme_id)
    path = theme_pack_path(normalized_theme_id, environ)
    if path is None:
        return ThemePackDetails(normalized_theme_id, label, None, "missing", "none")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ThemePackDetails(normalized_theme_id, label, path, "invalid", "unknown")
    name = data.get("name") if isinstance(data, dict) and isinstance(data.get("name"), str) else label
    inherits = data.get("inherits") if isinstance(data, dict) and isinstance(data.get("inherits"), str) else "none"
    errors = validate_theme_pack(data, theme_dir=path.parent, available_theme_ids=discover_theme_pack_ids(environ))
    if errors:
        return ThemePackDetails(normalized_theme_id, name, path, f"invalid: {errors[0]}", inherits)
    if inheritance_cycle(normalized_theme_id, environ):
        return ThemePackDetails(normalized_theme_id, name, path, "invalid: inheritance cycle", inherits)
    if not _inherited_packs_valid(normalized_theme_id, environ):
        return ThemePackDetails(normalized_theme_id, name, path, "invalid: inherits invalid theme", inherits)
    return ThemePackDetails(normalized_theme_id, name, path, "valid", inherits)


def shadowing_pack_paths(environ: dict[str, str] | None = None) -> tuple[tuple[str, Path], ...]:
    """User/system theme dirs whose name is a reserved built-in id. These packs
    never drive rendering (theme_pack_path serves built-in ids from the bundled
    dir only); they are reported so the user sees the override is ignored."""
    shadows: list[tuple[str, Path]] = []
    for theme_dir in (user_theme_dir(environ), system_theme_dir()):
        try:
            children = sorted(theme_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if normalized_theme_pack_reference(child.name) in BUILTIN_THEME_IDS and (child / "theme.json").exists():
                shadows.append((child.name, child / "theme.json"))
    return tuple(shadows)


def theme_pack_report_lines(environ: dict[str, str] | None = None) -> list[str]:
    lines = []
    for theme_id in discover_theme_pack_ids(environ):
        details = theme_pack_details(theme_id, environ)
        source = str(details.path) if details.path is not None else "not found"
        lines.append(f"{details.theme_id}\t{details.name}\t{details.status}\tinherits={details.inherits}\t{source}")
    for theme_id, path in shadowing_pack_paths(environ):
        label = THEME_LABELS.get(normalized_theme_pack_reference(theme_id), theme_id)
        lines.append(f"{theme_id}\t{label}\tinvalid: shadows built-in id\tinherits=none\t{path}")
    return lines


def _theme_source(theme_id: str, environ: dict[str, str] | None = None) -> str:
    if theme_id in BUILTIN_THEME_IDS:
        return "builtin"
    path = theme_pack_path(theme_id, environ)
    if path is None:
        return "builtin"
    return "system" if str(path).startswith(str(system_theme_dir())) else "user"


def _palette_with_color_overrides(base: ThemePalette, colors: dict) -> ThemePalette:
    updates: dict = {}
    for f in base.__dataclass_fields__.values():
        if f.name not in colors:
            continue
        if f.name == "restore_icon_background":
            hexval = colors[f.name].lstrip("#") if isinstance(colors[f.name], str) else ""
            if len(hexval) == 8:
                converted: tuple[int, ...] = tuple(int(hexval[i:i + 2], 16) for i in (0, 2, 4, 6))
                if converted != getattr(base, f.name):
                    updates[f.name] = converted
        else:
            if colors[f.name] != getattr(base, f.name):
                updates[f.name] = colors[f.name]
    return _dc_replace(base, **updates) if updates else base


def resolve_theme(theme: str | None = None, environ: dict[str, str] | None = None) -> ResolvedTheme:
    """Build the full theme surface from pack JSON + builtin palette. Not cached — reads environ fresh.
    Call invalidate_theme_cache() after a theme change to clear the theme_palette hot-path cache."""
    theme_id = normalize_theme_id(theme)
    if theme_id not in BUILTIN_THEME_IDS and theme_pack_details(theme_id, environ).status != "valid":
        # An invalid pack — missing, malformed, cyclic, or inheriting an invalid
        # parent — must never drive rendering, even via a direct resolve_theme()
        # call that bypasses the discover_valid_theme_ids() gate at the edges.
        # The fallback object identifies honestly as the builtin Dracula safe
        # default (not the invalid id the caller asked for), so consumers that
        # read .id/.source see the truth.
        return ResolvedTheme(
            id=DRACULA_THEME_ID,
            source="builtin",
            palette=THEMES[DRACULA_THEME_ID],
        )
    pack = load_theme_pack(theme_id, environ)
    inherits = pack.get("inherits") if isinstance(pack, dict) else None
    base_id = normalize_theme_id(inherits) if inherits else theme_id
    if base_id in THEMES:
        base_palette = THEMES[base_id]
    elif base_id == theme_id:
        # No (or self-referential) inherit on a non-builtin pack: default base.
        base_palette = THEMES[DRACULA_THEME_ID]
    else:
        # base_id is another user/system pack: resolve it so its own inherited
        # palette carries down. Safe from infinite recursion because the cycle
        # guard above fires for any cyclic chain reachable from theme_id.
        base_palette = resolve_theme(base_id, environ).palette
    colors = pack.get("colors", {}) if isinstance(pack.get("colors"), dict) else {}
    palette = _palette_with_color_overrides(base_palette, colors)
    opacity = pack["opacity"] if isinstance(pack.get("opacity"), (int, float)) else 1.0
    return ResolvedTheme(
        id=theme_id,
        source=_theme_source(theme_id, environ),
        palette=palette,
        opacity=float(opacity),
        font=dict(pack["font"]) if isinstance(pack.get("font"), dict) else {},
        spacing=dict(pack["spacing"]) if isinstance(pack.get("spacing"), dict) else {},
        corner_radius=dict(pack["corner_radius"]) if isinstance(pack.get("corner_radius"), dict) else {},
        border_width=dict(pack["border_width"]) if isinstance(pack.get("border_width"), dict) else {},
        icons=dict(pack["icons"]) if isinstance(pack.get("icons"), dict) else {},
    )


@lru_cache(maxsize=None)
def theme_palette(theme: str | None = None) -> ThemePalette:
    # Hot path: memoized. resolve_theme runs only on a cache miss (i.e. after a theme
    # change clears this cache via invalidate_theme_cache), never per paint.
    return resolve_theme(theme).palette


def invalidate_theme_cache() -> None:
    theme_palette.cache_clear()
    key_paint_style.cache_clear()


def app_menu_style_sheet(
    theme: str | None = None,
    border: bool = True,
    menu_padding: str = "4px",
    item_padding: str = "5px 22px 5px 12px",
) -> str:
    palette = theme_palette(theme)
    border_style = f"1px solid {palette.panel_border}" if border else "0"
    return f"""
    QMenu {{
        background: {palette.menu_background};
        color: {palette.text};
        border: {border_style};
        border-radius: 8px;
        padding: {menu_padding};
    }}
    QMenu::item {{
        padding: {item_padding};
        border-radius: 5px;
    }}
    QMenu::item:selected {{
        background: {palette.menu_selected_background};
    }}
    """


@lru_cache(maxsize=None)
def key_paint_style(is_hovered: bool, is_pressed: bool, is_locked: bool = False, theme: str | None = None) -> KeyPaintStyle:
    palette = theme_palette(theme)
    if is_pressed or is_locked:
        return KeyPaintStyle(
            top_color=palette.key_locked_top,
            bottom_color=palette.key_locked_bottom,
            border_color=palette.key_locked_border,
            border_width=5,
        )
    if is_hovered:
        return KeyPaintStyle(
            top_color=palette.key_hover_top,
            bottom_color=palette.key_hover_bottom,
            border_color=palette.key_hover_border,
            border_width=3,
        )
    return KeyPaintStyle(
        top_color=palette.key_normal_top,
        bottom_color=palette.key_normal_bottom,
        border_color=palette.key_normal_border,
        border_width=3,
    )


# QColor is imported lazily in the two helpers below so that importing this
# module (e.g. from the `--doctor`/`--help` CLI paths via doctor.py) does not
# pull in PySide6.QtGui unless an actual Qt color is requested.
def restore_icon_foreground_color(theme: str | None = None):
    from PySide6.QtGui import QColor

    return QColor(theme_palette(theme).restore_icon_foreground)


def restore_icon_background_color(theme: str | None = None):
    from PySide6.QtGui import QColor

    return QColor(*theme_palette(theme).restore_icon_background)
