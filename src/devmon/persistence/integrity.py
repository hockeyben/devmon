"""Tamper-evident save integrity: HMAC-SHA256 checksums over GameState.

The integrity key is shared across all profiles (one key file at the
top-level data dir, NOT profile-scoped) while the checksum sidecar
(`save.integrity`) lives alongside each profile's `save.json`.

Design:
- get_or_create_integrity_key(): reads/creates `<data dir>/.integrity_key`
  (hex-encoded 32 random bytes via secrets.token_bytes). Best-effort
  chmod 0o600 (POSIX only; no-op effectively on Windows).
- compute_checksum(state, key): canonical JSON (sorted keys) HMAC-SHA256 hex
  digest, so the checksum is stable regardless of Pydantic v2's dict key
  ordering.
- verify_checksum(state, key, stored): constant-time comparison.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets

from devmon.models.state import GameState
from devmon.persistence.save import _base_dir

INTEGRITY_KEY_FILENAME = ".integrity_key"


def get_or_create_integrity_key() -> bytes:
    """Return the shared HMAC key, generating and persisting it if absent."""
    base = _base_dir()
    base.mkdir(parents=True, exist_ok=True)
    key_path = base / INTEGRITY_KEY_FILENAME

    if key_path.exists():
        try:
            hex_text = key_path.read_text(encoding="utf-8").strip()
            key = bytes.fromhex(hex_text)
            if len(key) == 32:
                return key
        except (OSError, ValueError):
            pass

    key = secrets.token_bytes(32)
    key_path.write_text(key.hex(), encoding="utf-8")
    try:
        os.chmod(key_path, 0o600)
    except Exception:
        # Best-effort only -- Windows ACLs / permission errors are not fatal.
        pass
    return key


def compute_checksum(state: GameState, key: bytes) -> str:
    """Compute an HMAC-SHA256 hex digest over a canonical JSON serialization
    of `state` (sorted keys, so Pydantic v2's non-guaranteed dict ordering
    doesn't produce spurious mismatches)."""
    canonical = json.dumps(state.model_dump(mode="json"), sort_keys=True).encode()
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


def verify_checksum(state: GameState, key: bytes, stored: str) -> bool:
    """Constant-time comparison of a freshly computed checksum against `stored`."""
    return hmac.compare_digest(compute_checksum(state, key), stored)
