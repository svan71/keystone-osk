from logic_test_helpers import *

from keystone_osk.config import legacy_window_state_path

def test_config_paths_use_keystone_xdg_dirs() -> None:
    environ = {
        "XDG_CONFIG_HOME": "/home/user/.config",
        "XDG_DATA_HOME": "/home/user/.local/share",
        "XDG_STATE_HOME": "/home/user/.local/state",
    }

    assert window_state_path(environ) == Path("/home/user/.local/state/keystone-osk/window-state.json")
    assert legacy_window_state_path(environ) == Path("/home/user/.config/keystone-osk/window-state.json")
    assert learned_words_path(environ) == Path("/home/user/.local/state/keystone-osk/words.json")
    assert user_theme_dir(environ) == Path("/home/user/.local/share/keystone/themes")

def test_config_paths_honor_file_overrides() -> None:
    environ = {
        "KEYSTONE_OSK_STATE_FILE": "/tmp/keystone-window.json",
        "KEYSTONE_OSK_WORDS_FILE": "/tmp/keystone-words.json",
    }

    assert window_state_path(environ) == Path("/tmp/keystone-window.json")
    assert learned_words_path(environ) == Path("/tmp/keystone-words.json")
