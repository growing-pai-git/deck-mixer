"""The Claude Desktop bundle manifest (mcpb/manifest.json) must only pass
settings the server actually reads, each backed by an install-form field."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

MANIFEST = Path(__file__).parents[2] / "mcpb" / "manifest.json"

pytestmark = pytest.mark.skipif(not MANIFEST.exists(), reason="no mcpb/ in this checkout")


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_env_vars_are_settings_the_server_reads():
    from deck_mixer.config import _KNOWN_KEYS
    env = _manifest()["server"]["mcp_config"]["env"]
    for name in env:
        if name != "DECK_MIXER_BUNDLE":
            assert name.lower() in _KNOWN_KEYS, f"{name} is not a deck-mixer setting"


def test_env_placeholders_match_user_config():
    m = _manifest()
    refs = {r for v in m["server"]["mcp_config"]["env"].values()
            for r in re.findall(r"\$\{user_config\.([a-z_]+)\}", v)}
    assert refs == set(m["user_config"])


def test_keys_are_sensitive_and_nothing_is_required():
    for name, field in _manifest()["user_config"].items():
        assert not field.get("required"), f"{name} must stay optional (zero-config demo)"
        if name.endswith(("_key", "_token")):
            assert field.get("sensitive"), f"{name} must be stored in the OS keychain"


def test_declared_tools_match_the_server():
    import asyncio
    pytest.importorskip("mcp")
    from deck_mixer.server import mcp
    live = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {t["name"] for t in _manifest()["tools"]} == live
