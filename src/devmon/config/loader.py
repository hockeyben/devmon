"""TOML configuration loader for DevMon CLI.

Exports:
    load_config() -> dict  — Read config.toml (or return defaults if absent).
    save_config(cfg)       — Write config.toml to DEVMON_HOME (or platformdirs path).

Config path resolution (D-08: DEVMON_HOME override):
    If DEVMON_HOME is set: {DEVMON_HOME}/config.toml
    Otherwise:             {platformdirs.user_data_dir("devmon", "devmon")}/config.toml

Architecture note: This module must NOT import the EventBus bus singleton.
Only main.py and commands/ may use the bus.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_data_dir

from devmon.config.defaults import DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _config_path() -> Path:
    """Resolve the config.toml path using DEVMON_HOME if set (D-08).

    Returns:
        pathlib.Path pointing to config.toml (may not exist yet).
    """
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        return Path(devmon_home) / "config.toml"
    return Path(user_data_dir("devmon", "devmon")) / "config.toml"


def _deep_copy(d: dict) -> dict:
    """Return a shallow-recursive copy of *d*.

    Top-level values that are dicts are themselves copied one level deep.
    Sufficient for the two-level DEFAULT_CONFIG structure.

    Args:
        d: Dict to copy.

    Returns:
        New dict with copied top-level values.
    """
    result: dict = {}
    for key, value in d.items():
        if isinstance(value, dict):
            result[key] = dict(value)
        elif isinstance(value, list):
            result[key] = list(value)
        else:
            result[key] = value
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge *override* into *base*, returning a new dict.

    Nested dicts are merged recursively: missing keys are filled from base,
    existing keys in override win. Non-dict values from override always win.

    Args:
        base: Default values dict.
        override: User-supplied values dict (wins on conflict).

    Returns:
        Merged dict where override values take precedence.
    """
    merged: dict = _deep_copy(base)
    for key, override_value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(override_value, dict):
            merged[key] = _deep_merge(merged[key], override_value)
        else:
            merged[key] = override_value
    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config() -> dict[str, Any]:
    """Load configuration from config.toml, falling back to defaults.

    Resolution:
    - If config.toml does not exist: return a deep copy of DEFAULT_CONFIG.
    - If config.toml exists: parse it and deep-merge with DEFAULT_CONFIG
      (user values win; missing keys filled from defaults).

    Returns:
        Dict with keys "game", "ui", "shell" guaranteed to be present.
    """
    path = _config_path()
    if not path.exists():
        return _deep_copy(DEFAULT_CONFIG)

    with path.open("rb") as fh:
        user_cfg = tomllib.load(fh)

    return _deep_merge(DEFAULT_CONFIG, user_cfg)


def save_config(cfg: dict[str, Any]) -> None:
    """Write *cfg* to config.toml in the resolved config directory.

    Creates parent directories as needed (parents=True, exist_ok=True).

    Args:
        cfg: Configuration dict to serialize as TOML.
    """
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        tomli_w.dump(cfg, fh)
