"""Missing API keys are announced every time, with what they cost and how to add one."""

from __future__ import annotations

import pytest

KEYS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
        "STABILITY_API_KEY", "TOGETHER_API_KEY", "FAL_KEY", "REPLICATE_API_TOKEN",
        "PEXELS_API_KEY", "UNSPLASH_ACCESS_KEY", "LLM_PROVIDER", "IMAGE_PROVIDER")


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    for var in KEYS:
        monkeypatch.delenv(var, raising=False)


def test_notice_names_what_is_missing_and_how_to_fix_it():
    from deck_mixer.keys import GEMINI_KEY_URL, HOW_CLI, missing_keys_notice
    notice = missing_keys_notice(text=True, images=True, how=HOW_CLI)
    assert "Text:" in notice and "Images:" in notice
    assert GEMINI_KEY_URL in notice and "configure --gemini-api-key" in notice


def test_notice_only_mentions_what_the_deck_uses():
    from deck_mixer.keys import HOW_CLI, missing_keys_notice
    notice = missing_keys_notice(text=False, images=True, how=HOW_CLI)
    assert "Images:" in notice and "Text:" not in notice


def test_one_gemini_key_silences_it(monkeypatch):
    from deck_mixer.keys import HOW_CLI, missing_keys_notice
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert missing_keys_notice(text=True, images=True, how=HOW_CLI) == ""


def test_text_key_alone_still_asks_for_images(monkeypatch):
    from deck_mixer.keys import HOW_CLI, missing_keys_notice
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    notice = missing_keys_notice(text=True, images=True, how=HOW_CLI)
    assert "Images:" in notice and "Text:" not in notice
