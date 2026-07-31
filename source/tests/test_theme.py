# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os

from qt_window_test_helpers import *
import keystone_osk.theme as theme_module
import keystone_osk.state_io as state_io_module


def test_normalize_theme_id_sanitizes_case_and_whitespace() -> None:
    assert theme_module.normalize_theme_id("  Mocha ") == "mocha"
    assert theme_module.normalize_theme_id("default-dark") == "dark"  # alias resolves


def test_resolve_theme_id_accepts_builtin() -> None:
    assert theme_module.resolve_theme_id("mocha", theme_module.BUILTIN_THEME_IDS, strict=True) == "mocha"


def test_resolve_theme_id_strict_rejects_unknown() -> None:
    assert theme_module.resolve_theme_id("steev-kde", theme_module.BUILTIN_THEME_IDS, strict=True) is None


def test_resolve_theme_id_nonstrict_falls_back_to_safe_builtin() -> None:
    assert theme_module.resolve_theme_id("steev-kde", theme_module.BUILTIN_THEME_IDS, strict=False) == theme_module.DRACULA_THEME_ID


def test_resolve_theme_id_accepts_discovered_user_pack() -> None:
    discovered = theme_module.BUILTIN_THEME_IDS + ("custom-kde",)
    assert theme_module.resolve_theme_id("custom-kde", discovered, strict=True) == "custom-kde"


def test_first_run_theme_id_maps_color_scheme_to_generic_theme() -> None:
    assert theme_module.first_run_theme_id("dark") == "dark"
    assert theme_module.first_run_theme_id("light") == "light"
    assert theme_module.first_run_theme_id(None) == "dark"


def test_list_themes_prints_theme_pack_report_without_starting_qt(monkeypatch, capsys) -> None:
    monkeypatch.setattr(keyboard_app, "theme_pack_report_lines", lambda environ: ["dracula\tDracula\tvalid\tinherits=none\t/theme.json"])
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("theme listing started Qt"))

    assert keyboard_app.main(["--list-themes"]) == 0

    assert capsys.readouterr().out == "dracula\tDracula\tvalid\tinherits=none\t/theme.json\n"

def test_keyboard_theme_menu_action_toggles_to_mocha_and_back(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window._theme_actions["mocha"].trigger()

    assert window._theme_name == "mocha"
    assert window._theme_menu.title() == "Themes (Mocha)"
    assert window._theme_actions["mocha"].text() == "✓ Mocha"
    assert window._theme_actions["mocha"].isChecked()
    assert "background: #313244" in window._app_menu.styleSheet()

    window._theme_actions["dracula"].trigger()

    assert window._theme_name == "dracula"
    assert window._theme_menu.title() == "Themes (Dracula)"
    assert window._theme_actions["dracula"].text() == "✓ Dracula"

    window.close()

def test_keyboard_theme_persists_across_restart(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True, theme="dracula")

    window._toggle_keyboard_theme()
    window._save_window_state()
    window.close()
    restarted = KeyboardWindow(persist_window_state=True)

    assert load_keyboard_theme(state_path) == "mocha"
    assert restarted._theme_name == "mocha"
    assert restarted._theme_menu.title() == "Themes (Mocha)"
    assert restarted._theme_actions["mocha"].text() == "✓ Mocha"

    restarted.close()

def test_mocha_key_style_uses_catppuccin_palette() -> None:
    palette = theme_palette("mocha")
    style = key_paint_style(is_hovered=False, is_pressed=False, theme="mocha")

    assert palette.panel_top == "#1e1e2e"
    assert palette.panel_bottom == "#1e1e2e"
    assert palette.text == "#cdd6f4"
    assert palette.key_locked_border == "#cba6f7"
    assert palette.control_background == "#1e1e2e"
    assert palette.control_border == "#7b6398"
    assert style.top_color == "#202032"
    assert style.bottom_color == "#1e1e2e"
    assert style.border_color == "#6f5a88"

def test_dusk_preserves_original_mocha_labeled_palette() -> None:
    palette = theme_palette("dusk")
    style = key_paint_style(is_hovered=False, is_pressed=False, theme="dusk")

    assert palette.panel_top == "#1e1e2e"
    assert palette.panel_bottom == "#11111b"
    assert palette.text == "#cdd6f4"
    assert style.top_color == "#313244"
    assert style.bottom_color == "#181825"
    assert style.border_color == "#45475a"

def test_dracula_key_style_uses_actual_dracula_palette() -> None:
    palette = theme_palette("dracula")
    style = key_paint_style(is_hovered=False, is_pressed=False, theme="dracula")

    assert palette.panel_top == "#282a36"
    assert palette.panel_bottom == "#282a36"
    assert palette.text == "#f8f8f2"
    assert palette.key_locked_border == "#bd93f9"
    assert palette.control_background == "#282a36"
    assert palette.control_border == "#6a5487"
    assert style.top_color == "#2b2d39"
    assert style.bottom_color == "#282a36"
    assert style.border_color == "#5f4b78"

def test_midnight_uses_true_black_and_white_palette() -> None:
    palette = theme_palette("midnight")
    style = key_paint_style(is_hovered=False, is_pressed=False, theme="midnight")

    assert palette.panel_bottom == "#000000"
    assert palette.text == "#ffffff"
    assert palette.control_border == "#7b828b"
    assert palette.menu_selected_background == "#16181d"
    assert style.top_color == "#0f1012"
    assert style.bottom_color == "#030304"
    assert style.border_color == "#737982"

def test_dark_uses_soft_gray_dracula_labeled_palette() -> None:
    palette = theme_palette("dark")
    style = key_paint_style(is_hovered=False, is_pressed=False, theme="dark")

    assert palette.panel_top == "#1e1f29"
    assert palette.panel_bottom == "#111217"
    assert palette.text == "#f8f8f2"
    assert style.top_color == "#21222c"
    assert style.bottom_color == "#15161d"
    assert style.border_color == "#343746"

def test_light_key_style_uses_true_black_and_white_palette() -> None:
    palette = theme_palette("light")
    style = key_paint_style(is_hovered=False, is_pressed=False, theme="light")

    assert palette.panel_top == "#ffffff"
    assert palette.text == "#000000"
    assert style.top_color == "#ffffff"
    assert style.bottom_color == "#f2f2f2"
    assert style.border_color == "#999999"

def test_theme_pack_search_dirs_prefer_user_then_system_then_bundled() -> None:
    environ = {"XDG_DATA_HOME": "/home/user/.local/share"}

    assert user_theme_dir(environ) == keyboard_app.Path("/home/user/.local/share/keystone/themes")
    assert system_theme_dir() == keyboard_app.Path("/usr/share/keystone/themes")
    assert theme_pack_search_dirs(environ) == (
        keyboard_app.Path("/home/user/.local/share/keystone/themes"),
        keyboard_app.Path("/usr/share/keystone/themes"),
        bundled_theme_dir(),
    )

def test_builtin_theme_packs_exist_and_load() -> None:
    assert BUILTIN_THEME_IDS == ("dracula", "midnight", "mocha", "dusk", "dark", "light")
    assert default_theme_pack_id("dark") == "dark"
    assert default_theme_pack_id("light") == "light"
    assert default_theme_pack_id("default-dark") == "dark"
    assert default_theme_pack_id("default-light") == "light"

    for theme_id in BUILTIN_THEME_IDS:
        path = theme_pack_path(theme_id)
        assert path == bundled_theme_dir() / theme_id / "theme.json"
        data = load_theme_pack(theme_id)
        assert data["schema_version"] == 1
        assert data["id"] == theme_id
        assert {"colors", "font", "spacing", "corner_radius", "border_width"} <= set(data)
        assert "icons" not in data

def test_theme_packs_only_define_safe_customization_sections() -> None:
    for theme_id in BUILTIN_THEME_IDS:
        data = load_theme_pack(theme_id)
        assert set(data) <= THEME_PACK_SAFE_SECTIONS
        assert not (set(data) & THEME_PACK_FORBIDDEN_SECTIONS)

def test_missing_or_bad_theme_pack_loads_empty(tmp_path) -> None:
    missing_env = {"XDG_DATA_HOME": str(tmp_path)}
    assert theme_pack_path("missing-theme", missing_env) is None
    assert load_theme_pack("missing-theme", missing_env) == {}

    bad_theme_dir = tmp_path / "keystone" / "themes" / "broken"
    bad_theme_dir.mkdir(parents=True)
    (bad_theme_dir / "theme.json").write_text("{", encoding="utf-8")

    assert load_theme_pack("broken", missing_env) == {}

def test_theme_validation_rejects_unsafe_or_executable_sections() -> None:
    data = load_theme_pack("dracula")
    bad = {
        **data,
        "backend": "ydotool",
        "subprocess": "rm -rf",
        "colors": {**data["colors"], "text": "white"},
        "icons": {"tray": "../outside.svg"},
    }

    errors = validate_theme_pack(bad, theme_dir=bundled_theme_dir() / "dracula")

    assert "unsupported section: backend" in errors
    assert "unsupported section: subprocess" in errors
    assert "invalid color: text" in errors
    assert "invalid icon path: tray" in errors

def test_theme_validation_rejects_bad_schema_inheritance_and_metrics() -> None:
    data = {
        **load_theme_pack("mocha"),
        "schema_version": 999,
        "id": "../mocha",
        "inherits": "missing",
        "font": {"family": "Noto Sans", "size": 42},
        "spacing": {"key_gap": 1},
        "corner_radius": {"key": 99},
        "border_width": {"key": 5},
        "opacity": 0.2,
    }

    errors = validate_theme_pack(data, theme_dir=bundled_theme_dir() / "mocha")

    assert "unsupported schema_version" in errors
    assert "unsafe theme id" in errors
    assert "invalid inherits" in errors
    assert "font.size out of range" in errors
    assert "spacing.key_gap out of range" in errors
    assert "corner_radius.key out of range" in errors
    assert "border_width.key out of range" in errors
    assert "opacity out of range" in errors


def _write_pack(tmp_path, theme_id, data):
    # user_theme_dir uses XDG_DATA_HOME / "keystone" / "themes"
    pack_dir = tmp_path / "keystone" / "themes" / theme_id
    pack_dir.mkdir(parents=True)
    (pack_dir / "theme.json").write_text(json.dumps({"schema_version": 1, "id": theme_id, **data}), encoding="utf-8")
    return pack_dir


def test_resolved_theme_applies_pack_colors(tmp_path, monkeypatch) -> None:
    _write_pack(tmp_path, "custom-kde", {"inherits": "dracula", "colors": {"text": "#abcdef"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("custom-kde")
    assert resolved.palette.text == "#abcdef"
    assert resolved.palette.panel_top == theme_module.THEMES["dracula"].panel_top  # inherited untouched


def test_resolved_theme_defaults_opacity_to_one(tmp_path, monkeypatch) -> None:
    _write_pack(tmp_path, "custom-kde", {"inherits": "dracula", "colors": {}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert theme_module.resolve_theme("custom-kde").opacity == 1.0


def test_resolved_theme_applies_opacity(tmp_path, monkeypatch) -> None:
    _write_pack(tmp_path, "custom-kde", {"inherits": "dracula", "opacity": 0.85})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert theme_module.resolve_theme("custom-kde").opacity == 0.85


def test_resolved_theme_exposes_metrics_and_icons(tmp_path, monkeypatch) -> None:
    _write_pack(tmp_path, "custom-kde", {
        "inherits": "dracula",
        "font": {"size": 16},
        "spacing": {"key_gap": 8},
        "icons": {"tray": "icons/t.svg"},
    })
    (tmp_path / "keystone" / "themes" / "custom-kde" / "icons").mkdir()
    (tmp_path / "keystone" / "themes" / "custom-kde" / "icons" / "t.svg").write_text("<svg/>", encoding="utf-8")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("custom-kde")
    assert resolved.font.get("size") == 16
    assert resolved.spacing.get("key_gap") == 8
    assert resolved.icons.get("tray") == "icons/t.svg"


def test_resolve_theme_builtin_has_default_surface() -> None:
    resolved = theme_module.resolve_theme("mocha")
    assert resolved.palette == theme_module.THEMES["mocha"]
    assert resolved.opacity == 1.0
    assert isinstance(resolved.icons, dict)


def test_theme_menu_choices_lists_builtins_alphabetically() -> None:
    choices = theme_module.theme_menu_choices({"XDG_DATA_HOME": "/nonexistent-xdg-home"})
    labels = [label for _id, label in choices][: len(theme_module.BUILTIN_THEME_IDS)]
    assert labels == ["Dark", "Dracula", "Dusk", "Light", "Midnight", "Mocha"]


def test_theme_menu_choices_includes_user_packs_last(tmp_path, monkeypatch) -> None:
    pack_dir = tmp_path / "keystone" / "themes" / "custom-kde"
    pack_dir.mkdir(parents=True)
    (pack_dir / "theme.json").write_text('{"schema_version":1,"id":"custom-kde","name":"Custom KDE"}', encoding="utf-8")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    choices = theme_module.theme_menu_choices(dict(os.environ))
    ids = [c[0] for c in choices]
    assert set(ids[: len(theme_module.BUILTIN_THEME_IDS)]) == set(theme_module.BUILTIN_THEME_IDS)
    assert "custom-kde" in ids and ids.index("custom-kde") >= len(theme_module.BUILTIN_THEME_IDS)
    assert dict(choices)["custom-kde"] == "Custom KDE"


def _write_pack_full(tmp_path, theme_id, inherits=None):
    pack_dir = tmp_path / "keystone" / "themes" / theme_id
    pack_dir.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": 1, "id": theme_id}
    if inherits is not None:
        data["inherits"] = inherits
    (pack_dir / "theme.json").write_text(json.dumps(data), encoding="utf-8")


def test_inheritance_direct_cycle_is_rejected(tmp_path, monkeypatch) -> None:
    _write_pack_full(tmp_path, "acyc", inherits="bcyc")
    _write_pack_full(tmp_path, "bcyc", inherits="acyc")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    details = theme_module.theme_pack_details("acyc", dict(os.environ))
    assert details.status.startswith("invalid")
    assert "cycle" in details.status


def test_inheritance_indirect_cycle_is_rejected(tmp_path, monkeypatch) -> None:
    _write_pack_full(tmp_path, "acyc", inherits="bcyc")
    _write_pack_full(tmp_path, "bcyc", inherits="ccyc")
    _write_pack_full(tmp_path, "ccyc", inherits="acyc")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert "cycle" in theme_module.theme_pack_details("acyc", dict(os.environ)).status


def test_inheritance_valid_chain_ok(tmp_path, monkeypatch) -> None:
    _write_pack_full(tmp_path, "achain", inherits="dracula")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert theme_module.theme_pack_details("achain", dict(os.environ)).status == "valid"


def test_resolve_theme_cyclic_falls_back_to_builtin(tmp_path, monkeypatch) -> None:
    _write_pack_full(tmp_path, "acyc", inherits="bcyc")
    _write_pack_full(tmp_path, "bcyc", inherits="acyc")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("acyc", dict(os.environ))
    assert resolved.palette == theme_module.THEMES[theme_module.DRACULA_THEME_ID]


def test_opacity_validation_accepts_in_range() -> None:
    assert theme_module.validate_theme_pack({"schema_version": 1, "id": "a", "opacity": 0.9}) == ()


def test_opacity_validation_rejects_below_min() -> None:
    assert "opacity out of range" in theme_module.validate_theme_pack({"schema_version": 1, "id": "a", "opacity": 0.3})


def test_opacity_validation_rejects_above_max() -> None:
    assert "opacity out of range" in theme_module.validate_theme_pack({"schema_version": 1, "id": "a", "opacity": 1.5})


def test_theme_display_label_for_user_pack(tmp_path, monkeypatch) -> None:
    pack_dir = tmp_path / "keystone" / "themes" / "custom-kde"
    pack_dir.mkdir(parents=True)
    (pack_dir / "theme.json").write_text('{"schema_version":1,"id":"custom-kde","name":"Custom KDE"}', encoding="utf-8")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert theme_module.theme_display_label("custom-kde", dict(os.environ)) == "Custom KDE"
    assert theme_module.theme_display_label("mocha") == theme_module.THEME_LABELS["mocha"]


def test_user_pack_inherits_parent_user_pack_colors(tmp_path, monkeypatch) -> None:
    # Parent inherits a builtin and recolors `text`; child inherits the PARENT
    # user pack and recolors `panel_top`. The child must keep the parent's
    # `text` (not fall back to the builtin) and add its own `panel_top`.
    _write_pack(tmp_path, "uparent", {"inherits": "dracula", "colors": {"text": "#aaaaaa"}})
    _write_pack(tmp_path, "uchild", {"inherits": "uparent", "colors": {"panel_top": "#bbbbbb"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("uchild", dict(os.environ))
    assert resolved.palette.text == "#aaaaaa"        # inherited from parent user pack
    assert resolved.palette.panel_top == "#bbbbbb"   # child's own override


def test_three_level_user_inheritance_composes_colors(tmp_path, monkeypatch) -> None:
    # builtin <- lvl1 <- lvl2 <- lvl3, each contributing a distinct color.
    _write_pack(tmp_path, "lvl1", {"inherits": "dracula", "colors": {"text": "#111111"}})
    _write_pack(tmp_path, "lvl2", {"inherits": "lvl1", "colors": {"panel_top": "#222222"}})
    _write_pack(tmp_path, "lvl3", {"inherits": "lvl2", "colors": {"panel_bottom": "#333333"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("lvl3", dict(os.environ))
    assert resolved.palette.text == "#111111"          # from lvl1
    assert resolved.palette.panel_top == "#222222"      # from lvl2
    assert resolved.palette.panel_bottom == "#333333"   # lvl3's own


def test_single_level_inherit_from_builtin_unchanged(tmp_path, monkeypatch) -> None:
    # Regression: inheriting directly from a builtin still uses the builtin base.
    _write_pack(tmp_path, "uonly", {"inherits": "mocha", "colors": {"text": "#cafe01"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("uonly", dict(os.environ))
    assert resolved.palette.text == "#cafe01"  # own override
    assert resolved.palette.panel_top == theme_module.THEMES["mocha"].panel_top  # builtin base intact


def test_discover_valid_theme_ids_includes_builtins_and_valid_packs_only(tmp_path, monkeypatch) -> None:
    # Write one valid pack (inherits dracula, valid schema) and one invalid pack (bad schema_version)
    valid_dir = tmp_path / "keystone" / "themes" / "valid-pack"
    valid_dir.mkdir(parents=True)
    (valid_dir / "theme.json").write_text(
        json.dumps({"schema_version": 1, "id": "valid-pack", "inherits": "dracula"}),
        encoding="utf-8",
    )
    invalid_dir = tmp_path / "keystone" / "themes" / "broken-pack"
    invalid_dir.mkdir(parents=True)
    (invalid_dir / "theme.json").write_text(
        json.dumps({"schema_version": 99, "id": "broken-pack"}),
        encoding="utf-8",
    )
    environ = {**os.environ, "XDG_DATA_HOME": str(tmp_path)}
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    all_ids = theme_module.discover_theme_pack_ids(environ)
    valid_ids = theme_module.discover_valid_theme_ids(environ)

    # discover_theme_pack_ids must still include both (raw discovery unchanged)
    assert "valid-pack" in all_ids
    assert "broken-pack" in all_ids

    # discover_valid_theme_ids: all builtins first, then only the valid user pack
    assert list(valid_ids[: len(theme_module.BUILTIN_THEME_IDS)]) == list(theme_module.BUILTIN_THEME_IDS)
    assert "valid-pack" in valid_ids
    assert "broken-pack" not in valid_ids


def test_cyclic_user_parent_chain_falls_back_without_recursion_error(tmp_path, monkeypatch) -> None:
    # Child inherits into a mutually-cyclic parent pair. The cycle guard must
    # catch it for the whole chain and fall back to dracula — no infinite
    # recursion through the new recursive base resolution.
    _write_pack(tmp_path, "kcyc_a", {"inherits": "kcyc_b"})
    _write_pack(tmp_path, "kcyc_b", {"inherits": "kcyc_a"})
    _write_pack(tmp_path, "kcyc_child", {"inherits": "kcyc_a", "colors": {"text": "#cccccc"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("kcyc_child", dict(os.environ))
    assert resolved.palette == theme_module.THEMES[theme_module.DRACULA_THEME_ID]


# --- Review item 4: a pack may inherit only from valid ancestors ---

def test_inheriting_from_invalid_pack_is_rejected(tmp_path, monkeypatch) -> None:
    # `badbase` is structurally invalid (bad color); `kid` inherits it. The kid
    # must NOT be considered valid just because `badbase` exists as a raw id.
    _write_pack(tmp_path, "badbase", {"inherits": "dracula", "colors": {"text": "notahex"}})
    _write_pack(tmp_path, "kid", {"inherits": "badbase"})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    env = dict(os.environ)
    assert theme_module.theme_pack_details("badbase", env).status.startswith("invalid")
    assert theme_module.theme_pack_details("kid", env).status.startswith("invalid")


def test_inheriting_from_valid_user_pack_stays_valid(tmp_path, monkeypatch) -> None:
    # Regression guard for the item-4 fix: a valid chain through a user pack
    # (not just a builtin) must stay valid.
    _write_pack(tmp_path, "goodbase", {"inherits": "dracula", "colors": {"text": "#abcdef"}})
    _write_pack(tmp_path, "goodkid", {"inherits": "goodbase"})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    env = dict(os.environ)
    assert theme_module.theme_pack_details("goodbase", env).status == "valid"
    assert theme_module.theme_pack_details("goodkid", env).status == "valid"


def test_discover_valid_theme_ids_excludes_child_of_invalid_pack(tmp_path, monkeypatch) -> None:
    _write_pack(tmp_path, "badbase", {"inherits": "dracula", "colors": {"text": "notahex"}})
    _write_pack(tmp_path, "kid", {"inherits": "badbase"})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    valid_ids = theme_module.discover_valid_theme_ids(dict(os.environ))
    assert "badbase" not in valid_ids
    assert "kid" not in valid_ids


# --- Review item 3: only valid themes may become active or persisted ---

def test_save_keyboard_theme_does_not_persist_invalid_pack(tmp_path, monkeypatch) -> None:
    # An invalid (but raw-discoverable) pack must not be persisted as active.
    _write_pack(tmp_path, "badactive", {"schema_version": 99})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    state_path = tmp_path / "state.json"
    state_io_module.save_keyboard_theme("badactive", state_path)
    assert state_io_module.load_keyboard_theme(state_path) == theme_module.DRACULA_THEME_ID


def test_load_keyboard_theme_ignores_persisted_invalid_pack(tmp_path, monkeypatch) -> None:
    # A state file that already holds an invalid theme id must not activate it.
    _write_pack(tmp_path, "badactive", {"schema_version": 99})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"theme": "badactive"}), encoding="utf-8")
    assert state_io_module.load_keyboard_theme(state_path) == theme_module.DRACULA_THEME_ID


def test_control_theme_rejects_invalid_pack(app, tmp_path, monkeypatch) -> None:
    # The control path must reject a raw-discoverable but invalid pack instead of
    # activating it.
    _write_pack(tmp_path, "badctl", {"schema_version": 99})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        assert window._control_theme("badctl") == "ERR invalid theme"
        assert window._theme_name != "badctl"
    finally:
        window.close()


def test_resolve_theme_rejects_invalid_inherited_pack(tmp_path, monkeypatch) -> None:
    # A pack inheriting an invalid pack is itself invalid; a *direct*
    # resolve_theme() call must not render it. Invalid packs never drive paint.
    _write_pack(tmp_path, "badbase", {"colors": {"text": "ZZZZZZ"}})  # bad hex -> invalid
    _write_pack(tmp_path, "kid", {"inherits": "badbase", "colors": {"text": "#abcdef"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("kid", dict(os.environ))
    assert resolved.palette == theme_module.THEMES[theme_module.DRACULA_THEME_ID]


def test_load_theme_pack_rejects_inherited_invalid(tmp_path, monkeypatch) -> None:
    # public3 item 3: load_theme_pack() itself must not return data for a pack
    # that inherits an invalid parent, even via a direct call that bypasses the
    # rendering-edge gates.
    _write_pack(tmp_path, "badbase", {"colors": {"text": "ZZZZZZ"}})  # bad hex -> invalid
    _write_pack(tmp_path, "kid", {"inherits": "badbase", "colors": {"text": "#abcdef"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert theme_module.load_theme_pack("kid", dict(os.environ)) == {}


def test_load_theme_pack_rejects_cyclic(tmp_path, monkeypatch) -> None:
    _write_pack_full(tmp_path, "acyc", inherits="bcyc")
    _write_pack_full(tmp_path, "bcyc", inherits="acyc")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert theme_module.load_theme_pack("acyc", dict(os.environ)) == {}


def test_load_theme_pack_returns_valid_pack(tmp_path, monkeypatch) -> None:
    # The gate must not over-reject: a fully valid pack still loads.
    _write_pack(tmp_path, "ok", {"inherits": "dracula", "colors": {"text": "#abcdef"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    data = theme_module.load_theme_pack("ok", dict(os.environ))
    assert data.get("colors", {}).get("text") == "#abcdef"


def test_resolve_theme_invalid_fallback_identifies_as_builtin(tmp_path, monkeypatch) -> None:
    # public3 item 4: the safe fallback object must tell the truth -- it is the
    # builtin Dracula theme, not the invalid id the caller asked for.
    _write_pack(tmp_path, "badbase", {"colors": {"text": "ZZZZZZ"}})
    _write_pack(tmp_path, "kid", {"inherits": "badbase", "colors": {"text": "#abcdef"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("kid", dict(os.environ))
    assert resolved.id == theme_module.DRACULA_THEME_ID
    assert resolved.source == "builtin"
    assert resolved.opacity == 1.0


def test_resolve_theme_builtin_ignores_user_shadow_pack(tmp_path, monkeypatch) -> None:
    # A user pack named after a built-in id must never override the built-in.
    _write_pack(tmp_path, "dracula", {"colors": {"text": "#abcdef"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    resolved = theme_module.resolve_theme("dracula", dict(os.environ))
    assert resolved.palette == theme_module.THEMES[theme_module.DRACULA_THEME_ID]


def test_shadowing_pack_paths_detects_builtin_collision(tmp_path, monkeypatch) -> None:
    _write_pack(tmp_path, "dracula", {"colors": {"text": "#abcdef"}})        # shadow
    _write_pack(tmp_path, "custom-kde", {"inherits": "dracula"})              # legit, not a shadow
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    ids = [s[0] for s in theme_module.shadowing_pack_paths(dict(os.environ))]
    assert "dracula" in ids
    assert "custom-kde" not in ids


def test_theme_pack_report_flags_builtin_shadow_as_invalid(tmp_path, monkeypatch) -> None:
    # The shadow surfaces in the pack report as invalid so --doctor warns on it.
    _write_pack(tmp_path, "dracula", {"colors": {"text": "#abcdef"}})
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    lines = theme_module.theme_pack_report_lines(dict(os.environ))
    shadow_lines = [l for l in lines if l.startswith("dracula\t") and "shadows built-in id" in l]
    assert shadow_lines and "invalid" in shadow_lines[0]
