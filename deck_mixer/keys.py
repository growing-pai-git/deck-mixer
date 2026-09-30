"""Tell people, every time, what a missing API key is costing their deck.

Decks still build with no keys, but the difference is large: AI slide
planning (text) and generated imagery (images) are what make a deck look
designed rather than templated. One free Gemini key covers both.
"""

from __future__ import annotations

import os

GEMINI_KEY_URL = "https://aistudio.google.com/apikey"

# How to add a key, per place the engine runs.
HOW_CLI = "Add it with:  pandoro deck-mixer configure --gemini-api-key <your key>"
HOW_MCP = ("Add it with  pandoro deck-mixer configure --gemini-api-key <your key>  in a "
           "terminal and restart Claude (keeps the key out of the chat), or ask Claude "
           "to run configure_keys with it.")
HOW_BUNDLE = ("Add it in Claude Desktop under Settings → Extensions → Deck Mixer, "
              "then build again.")


def has_text_key() -> bool:
    from . import llm
    return bool(llm.configured_providers())


def has_image_key() -> bool:
    from .imagegen import configured_providers
    return bool(configured_providers() or os.environ.get("PEXELS_API_KEY")
                or os.environ.get("UNSPLASH_ACCESS_KEY"))


def missing_keys_notice(*, text: bool, images: bool, how: str) -> str:
    """A short notice for a deck that would benefit from `text` (AI slide
    planning) and/or `images` keys; "" when everything it uses is set."""
    missing = []
    if text and not has_text_key():
        missing.append("Text: no AI slide planning, so layouts and headlines follow simple rules")
    if images and not has_image_key():
        missing.append("Images: grey placeholders instead of pictures")
    if not missing:
        return ""
    lines = "\n".join(f"  ✗ {m}" for m in missing)
    return ("⚠️  This deck was built without AI keys, so it looks basic:\n"
            f"{lines}\n"
            "For much better decks, add an API key. One free Gemini key covers "
            f"text and images: {GEMINI_KEY_URL}\n"
            f"{how}\n\n")
