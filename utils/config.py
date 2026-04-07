import json
import os
from typing import Any, Dict

# Repo-local config path (preferred)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
REPO_CONFIG_DIR = os.path.join(_REPO_ROOT, "config")
REPO_CONFIG_PATH = os.path.join(REPO_CONFIG_DIR, "file_config.json")

# Fallback user config path
USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "spectator")
USER_CONFIG_PATH = os.path.join(USER_CONFIG_DIR, "file_config.json")

_DEFAULTS: Dict[str, Any] = {
    # Base directory where date-stamped subdirectories live (e.g., /home/user/data/pdata)
    "default_data_base_dir": os.path.join(os.path.expanduser("~"), "data", "pdata"),
    # If true, the file chooser will auto-navigate into the most recent YYMMDD subdirectory
    "auto_navigate_recent": False,
    # Subdirectory name filter that must be in the path (previous default: 'reduced')
    "must_be_in_directory": "reduced",
    # Excluded filename terms
    "excluded_file_terms": ["cal", "dark", "ff"],
}


def load_config() -> Dict[str, Any]:
    """Load spectator config with defaults.

    Order of precedence:
    1) User-local: ~/.config/spectator/file_config.json
    2) Repo-local: REPO/config/file_config.json

    Returns:
        dict: Merged config with defaults applied for missing keys.
    """
    cfg: Dict[str, Any] = dict(_DEFAULTS)

    # 1) User config under ~/.config/spectator
    try:
        if os.path.isfile(USER_CONFIG_PATH):
            with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            if isinstance(user_cfg, dict):
                cfg.update(user_cfg)
            return cfg
    except Exception as e:
        # Non-fatal; fall back to defaults
        print(f"Warning: could not read user config at {USER_CONFIG_PATH}: {e}")

    # 2) Repo-local config
    try:
        if os.path.isfile(REPO_CONFIG_PATH):
            with open(REPO_CONFIG_PATH, "r", encoding="utf-8") as f:
                repo_cfg = json.load(f)
            if isinstance(repo_cfg, dict):
                cfg.update(repo_cfg)
            return cfg
    except Exception as e:
        print(f"Warning: could not read repo config at {REPO_CONFIG_PATH}: {e}")

    return cfg


def ensure_example_config():
    """Create a skeleton repo-local file_config.json if none exists (non-intrusive)."""
    try:
        os.makedirs(REPO_CONFIG_DIR, exist_ok=True)
        if not os.path.isfile(REPO_CONFIG_PATH):
            with open(REPO_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(_DEFAULTS, f, indent=2)
    except Exception:
        # Ignore errors silently
        pass
