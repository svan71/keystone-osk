# Keystone OSK

Practical on-screen keyboard for Linux desktops.

Keystone is a PySide6 application that uses `ydotool` for key output. A working
install needs `ydotoold` running and user access to `/dev/uinput`.

Run:

```bash
keystone-osk
```

Useful diagnostics:

```bash
keystone-osk --doctor
keystone-osk --status
keystone-osk --list-themes
```

Keystone runs on Qt's `xcb` platform by default, including on Wayland sessions,
where it runs through XWayland. Set `KEYSTONE_OSK_QT_PLATFORM=wayland` to opt
into Qt's native Wayland platform instead. GNOME and
KDE behavior profiles are supported. On GNOME the top-bar tray icon requires an
AppIndicator/KStatusNotifierItem extension (Arch: `gnome-shell-extension-appindicator`),
because GNOME has no built-in tray; `--doctor` reports this. Otherwise
tray behavior depends on the desktop shell,
and Keystone keeps its restore icon as the fallback when a real tray is
unavailable.
