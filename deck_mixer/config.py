"""Persistent user configuration for pandoro.

Stores API keys and user preferences in ~/.config/pandoro/keys.json
with restricted file permissions (owner read/write only).

Load order for each setting:
  1. Environment variable (highest priority — allows per-session override)
  2. keys.json config file
  3. Built-in default
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path


CONFIG_DIR  = Path.home() / ".config" / "pandoro"
CONFIG_FILE = CONFIG_DIR / "keys.json"

_KNOWN_KEYS = {
    # planning / "art director" LLM providers (layout, visual judgment, mood)
    "anthropic_api_key",
    "llm_provider",             # which planner LLM to use ("auto" or a provider name)
    # image generation providers
    "openai_api_key",
    "gemini_api_key",
    "stability_api_key",
    "together_api_key",
    "fal_key",
    "replicate_api_token",
    "image_provider",          # which generator to use ("auto" or a provider name)
    "image_theme",             # subject theme woven into every gen prompt (e.g. "artisan bakery")
    "image_art_style",         # rendering style for gen prompts (e.g. "Studio Ghibli anime style")
    "image_prefer_generate",   # truthy -> AI generation wins even on "photo" slots
    # stock photo providers
    "pexels_api_key",
    "unsplash_access_key",
    # case library + brand
    "library_path",             # path to a case-library folder (see CASE_LIBRARY_SCHEMA.md)
    "theme_path",                # path to a theme.yaml/theme.json (see theme.py)
    "brand_description",         # free-text brand description, used when no theme_path is set
    # misc
    "output_dir",
    "template_path",
}


def load_config() -> dict:
    """Return the persisted config dict, or {} if the file doesn't exist."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def is_first_run() -> bool:
    """True until the user has gone through setup (no keys.json written yet)."""
    return not CONFIG_FILE.exists()


def mark_setup_done() -> None:
    """Create the config file (possibly empty) so onboarding doesn't repeat."""
    if not CONFIG_FILE.exists():
        save_config({})


def save_config(updates: dict) -> None:
    """Merge `updates` into the existing config and write atomically."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current = load_config()
    # Remove keys explicitly set to None or "" (user clearing a value)
    for k, v in updates.items():
        if v:
            current[k] = v
        else:
            current.pop(k, None)
    CONFIG_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    # Restrict to owner read/write only
    CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def get(key: str, default: str | None = None) -> str | None:
    """
    Resolve a config value: env var → config file → default.

    `key` is the config file key (e.g. "anthropic_api_key").
    The corresponding env var is derived automatically:
      anthropic_api_key → ANTHROPIC_API_KEY
    """
    env_var = key.upper()
    env_val = os.environ.get(env_var)
    if env_val:
        return env_val
    return load_config().get(key, default)


def load_dotenv(search_paths: list[Path] | None = None) -> None:
    """Load KEY=VALUE lines from a gitignored `.env` file into os.environ
    (without overwriting existing vars). Looks in KB_PATH and the repo root.

    Lets users keep secrets in a local `.env` file, e.g.:
        GEMINI_API_KEY=AIza...
        IMAGE_PROVIDER=gemini_flash
    """
    if search_paths is None:
        search_paths = []
        if os.environ.get("LIBRARY_PATH"):
            search_paths.append(Path(os.environ["LIBRARY_PATH"]).expanduser())
        search_paths.append(Path(__file__).parent.parent)  # repo root
    seen = set()
    for base in search_paths:
        env_file = base / ".env"
        key = str(env_file.resolve()) if env_file.exists() else None
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and v and not os.environ.get(k):
                    os.environ[k] = v
        except OSError:
            pass


def inject_keys() -> None:
    """
    Push saved keys into os.environ for keys not already set.
    Reads a local `.env` first, then the keys.json config file. Call once at
    server startup so existing library code reads os.environ normally.
    """
    load_dotenv()
    cfg = load_config()
    for k, v in cfg.items():
        env_var = k.upper()
        if v and not os.environ.get(env_var):
            os.environ[env_var] = str(v)


def mask(value: str | None) -> str:
    """Return a display-safe masked version of an API key."""
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return "***"
    return value[:6] + "..." + value[-4:] + "  [set]"
