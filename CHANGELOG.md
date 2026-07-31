# Changelog

All notable changes to Keystone are recorded here. Versions follow
[semantic versioning](https://semver.org/). Keystone is pre-1.0 and under active
development: defaults, settings, and on-disk state formats may still change
between releases.

## [0.9.0] - 2026-07-31

First public beta.

### Added

- Compact and full keyboard layouts, switchable from the menu at runtime, with
  a numeric keypad in the full layout.
- Word completion backed by a bundled dictionary, plus learned words persisted
  per user.
- Accented and special characters through long-press on the relevant key.
- User-defined text snippets, with load-error reporting and a reset action.
- Six built-in themes (dark, light, dracula, dusk, midnight, mocha) and a theme
  pack system that supports user-supplied packs with inheritance and validation.
- Tray icon with show, hide, and toggle controls, falling back to an on-screen
  restore icon when the desktop shell provides no usable tray.
- Single-instance control socket, so `--show`, `--hide`, `--toggle`, `--theme`,
  and `--mode` drive an already-running instance. Suitable for binding to
  desktop keyboard shortcuts.
- `--doctor` diagnostic report covering the input backend, `ydotool`/`ydotoold`
  status, `/dev/uinput` permissions, session type, theme discovery, and the
  control socket.
- Window geometry and mode persistence across restarts, clamped to the current
  screen on restore.
- An About dialog.

### Known limitations

- Keyboard input is delivered through `ydotool`, which requires a running
  `ydotoold` and write access to `/dev/uinput`. Keystone cannot type until that
  is set up; `--doctor` reports what is missing.
- Because of the `/dev/uinput` requirement, Keystone is not currently
  distributable as a sandboxed Flatpak.
- Qt runs on the `xcb` platform by default, including on Wayland sessions, where
  Keystone runs through XWayland.

[0.9.0]: https://github.com/svan71/keystone-osk/releases/tag/v0.9.0
