"""Deck Mixer MCP bundle entry point — Claude Desktop runs this via `uv run`.

The manifest maps every install-form field to an env var. Optional fields the
user leaves blank arrive empty or as the unexpanded "${user_config.x}"
placeholder, so drop those before the server reads its configuration.
"""

import json
import os
from pathlib import Path

manifest = json.loads((Path(__file__).parent.parent / "manifest.json").read_text(encoding="utf-8"))
for name in manifest["server"]["mcp_config"]["env"]:
    value = os.environ.get(name)
    if value is not None and (not value.strip() or value.startswith("${user_config.")):
        del os.environ[name]

from deck_mixer.server import mcp  # noqa: E402  (reads the env above at import)

mcp.run()
