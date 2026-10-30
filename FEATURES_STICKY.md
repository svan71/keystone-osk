# Sticky Window Support

## Overview
This fork adds support for making the Keystone OSK keyboard window and its
restore icon appear on all workspaces simultaneously. This is especially useful
on GNOME Wayland where utility windows are tied to the current workspace by
default.

## Features

### 1. `--sticky` Command Line Flag
Start Keystone OSK with sticky windows enabled:

```bash
keystone-osk --sticky
```

This makes the main keyboard window appear on all workspaces immediately.

### 2. Automatic Sticky Restore Icon
When the keyboard is minimized/hidden, the floating restore icon is also made
sticky on all workspaces automatically.

### 3. `keystone-osk-sticky` Wrapper Script
A companion wrapper script that provides more reliable sticky window behavior
under GNOME Wayland by using `wmctrl` in addition to the built-in X11 property
setting:

```bash
keystone-osk-sticky --show        # Show keyboard (sticky)
keystone-osk-sticky --start-hidden # Start hidden (sticky when shown)
keystone-osk-sticky --sticky      # Same as --show with sticky guarantee
keystone-osk-sticky --quit        # Quit the keyboard
keystone-osk-sticky --status      # Show status
```

## Installation

### Option 1: From Source (Recommended)
```bash
cd source
pip install .
```

### Option 2: System Package
```bash
# For Arch Linux
cd packaging
makepkg -si
```

### Option 3: Manual
1. Copy the contents of `source/keystone_osk/` to your site-packages directory
2. Ensure `wmctrl` and `xprop` are installed
3. Copy `keystone-osk-sticky` to `~/.local/bin/`

## Autostart Setup

### GNOME Autostart
Add to your GNOME session autostart:

```bash
# The autostart.py automatically detects and uses the wrapper if available
keystone-osk --autostart
```

Or manually create `~/.config/autostart/keystone-osk.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Keystone OSK (Sticky)
Comment=On-screen keyboard with sticky window support
Exec=/home/username/.local/bin/keystone-osk-sticky --start-hidden
Icon=keystone
X-GNOME-Autostart-enabled=true
```

## Technical Details

### How It Works
1. **X11 Properties**: Under XWayland (the default on GNOME), the window sets
   `_NET_WM_STATE_STICKY` via `XChangeProperty` when the `set_window_sticky()`
   function is called.

2. **Desktop Assignment**: Sets `_NET_WM_DESKTOP` to `0xFFFFFFFF` (all desktops)
   to ensure the window appears on every workspace.

3. **WMCtrl Reinforcement**: The wrapper script additionally uses `wmctrl` to
   reinforce the sticky state and handle edge cases with GNOME's compositor.

4. **Background Monitoring**: The wrapper includes a background process that
   periodically checks and re-applies sticky properties to new windows (like
   the restore icon when the keyboard is minimized).

### Platform Support
- **GNOME Wayland**: Works via XWayland (xcb) with X11 properties
- **GNOME X11**: Native X11 support
- **KDE Plasma**: Partial support (KDE sessions use BypassWindowManagerHint)
- **Wayland Native**: Limited (requires compositor support for sticky windows)

## Credits
- Original Keystone OSK project by [svan71](https://github.com/svan71/keystone-osk)
- This fork maintained by [@crastatelvin](https://github.com/crastatelvin)
- GPL-3.0-or-later licensed
