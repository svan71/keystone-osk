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

Keystone prefers Qt's native Wayland platform when `WAYLAND_DISPLAY` is present.
Set `KEYSTONE_OSK_QT_PLATFORM=xcb` to use the XWayland/xcb fallback. GNOME and
KDE behavior profiles are supported; tray behavior depends on the desktop shell,
and Keystone keeps its restore icon as the fallback when a real tray is
unavailable.
