"""Pluggable branding for generated decks.

A `Theme` carries every brand decision the engine used to hardcode (colors,
fonts, logo, company name, tagline, mood/palette used to steer imagery) and
is threaded explicitly through the builders instead of being baked in.

Three ways to get one, in priority order (see `load_theme`):
  1. An explicit theme file (`theme.yaml`/`theme.json`) + asset files.
  2. A free-text `--brand-description`, inferred into a palette via an LLM.
  3. The bundled neutral default (works with zero configuration).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from pptx.dml.color import RGBColor


def _rgb(hex_str: str) -> RGBColor:
    return RGBColor.from_string(hex_str.lstrip("#").upper())


@dataclass
class Theme:
    # Identity
    company_name: str = "Pandoro"
    wordmark_text: str = "Pandoro"       # fallback text when no logo asset
    tagline: str = ""                    # closing slide; empty = company name / logo
    website: str = ""
    show_credit: bool = True             # small "Made with Deck Mixer" line on the closing slide

    # Assets (None = fall back to a drawn shape / text wordmark)
    logo_path: Path | None = None
    favicon_path: Path | None = None

    # Palette
    primary: RGBColor = field(default_factory=lambda: _rgb("1E293B"))       # deep slate
    primary_dark: RGBColor = field(default_factory=lambda: _rgb("131B28"))
    accent: RGBColor = field(default_factory=lambda: _rgb("14B8A6"))        # teal
    accent_dim: RGBColor = field(default_factory=lambda: _rgb("7DC9C0"))
    accent_text: RGBColor = field(default_factory=lambda: _rgb("0F8276"))
    secondary: RGBColor = field(default_factory=lambda: _rgb("F59E0B"))     # amber
    secondary_text: RGBColor = field(default_factory=lambda: _rgb("B06C02"))
    secondary_soft: RGBColor = field(default_factory=lambda: _rgb("FDECD1"))
    white: RGBColor = field(default_factory=lambda: _rgb("FFFFFF"))
    off_white: RGBColor = field(default_factory=lambda: _rgb("FBFCFC"))
    dark_text: RGBColor = field(default_factory=lambda: _rgb("1A202B"))
    mid_gray: RGBColor = field(default_factory=lambda: _rgb("5C6674"))
    light_bg: RGBColor = field(default_factory=lambda: _rgb("ECF1F0"))
    hairline: RGBColor = field(default_factory=lambda: _rgb("D8DEE2"))

    # Typography
    font_head: str = "Calibri"
    font_body: str = "Calibri"

    # Imagery mood — consumed by glaze/style.py to steer generated/stock photos
    mood: list[str] = field(default_factory=lambda: ["professional", "modern", "clean", "minimal"])
    palette_description: str = "teal and amber tones"
    subject_bias: str = "business technology"
    art_style: str = ""


DEFAULT_THEME = Theme()


_COLOR_FIELDS = (
    "primary", "primary_dark", "accent", "accent_dim", "accent_text",
    "secondary", "secondary_text", "secondary_soft", "white", "off_white",
    "dark_text", "mid_gray", "light_bg", "hairline",
)


def _load_theme_file(path: Path) -> Theme:
    """Load a theme.yaml/theme.json file. Asset paths are resolved relative
    to the file's directory. Unspecified fields keep the default's value."""
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)

    base_dir = path.parent
    kwargs: dict = {}

    for key in ("company_name", "wordmark_text", "tagline", "website",
                "font_head" , "font_body", "palette_description", "subject_bias",
                "art_style"):
        if key in data:
            kwargs[key] = data[key]
    if "credit" in data:
        kwargs["show_credit"] = bool(data["credit"])
    if "fonts" in data:
        fonts = data["fonts"] or {}
        if "head" in fonts:
            kwargs["font_head"] = fonts["head"]
        if "body" in fonts:
            kwargs["font_body"] = fonts["body"]
    if "mood" in data:
        kwargs["mood"] = list(data["mood"])

    colors = data.get("colors") or {}
    for name in _COLOR_FIELDS:
        if name in colors:
            kwargs[name] = _rgb(colors[name])

    assets = data.get("assets") or {}
    logo = assets.get("logo")
    favicon = assets.get("favicon")
    if logo:
        p = (base_dir / logo)
        kwargs["logo_path"] = p if p.exists() else None
    if favicon:
        p = (base_dir / favicon)
        kwargs["favicon_path"] = p if p.exists() else None

    return replace(DEFAULT_THEME, **kwargs)


def _infer_theme(description: str) -> Theme | None:
    """Ask an LLM to turn a free-text brand description into a palette +
    mood. Returns None if no LLM is configured or the call fails, so the
    caller can fall back to the default theme."""
    from .llm import call_json

    schema = {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "tagline": {"type": "string", "description": "Short punchy closing-slide tagline"},
            "primary": {"type": "string", "description": "Hex color, dark background/UI color"},
            "accent": {"type": "string", "description": "Hex color, primary accent"},
            "secondary": {"type": "string", "description": "Hex color, secondary accent"},
            "mood": {"type": "array", "items": {"type": "string"},
                     "description": "3-4 adjectives describing the visual feel"},
            "subject_bias": {"type": "string",
                             "description": "2-3 words for preferred imagery subjects"},
            "palette_description": {"type": "string",
                                    "description": "e.g. 'forest green and cream tones'"},
        },
        "required": ["company_name", "primary", "accent", "secondary", "mood"],
    }
    system = ("You are a brand designer. Given a free-text brand description, "
              "propose a cohesive deck theme: a dark primary color, an accent "
              "color and a secondary color (as hex strings, e.g. '1E293B'), "
              "chosen so accent/secondary read clearly as white text on the "
              "primary color and as dark text on white. Also propose a short "
              "tagline, imagery mood and subject bias.")
    data = call_json(system, description, schema)
    if not data:
        return None
    try:
        kwargs = {
            "company_name": data.get("company_name") or DEFAULT_THEME.company_name,
            "wordmark_text": data.get("company_name") or DEFAULT_THEME.wordmark_text,
            "primary": _rgb(data["primary"]),
            "accent": _rgb(data["accent"]),
            "accent_text": _rgb(data["accent"]),
            "secondary": _rgb(data["secondary"]),
            "secondary_text": _rgb(data["secondary"]),
        }
        if data.get("tagline"):
            kwargs["tagline"] = data["tagline"]
        if data.get("mood"):
            kwargs["mood"] = list(data["mood"])
        if data.get("subject_bias"):
            kwargs["subject_bias"] = data["subject_bias"]
        if data.get("palette_description"):
            kwargs["palette_description"] = data["palette_description"]
        return replace(DEFAULT_THEME, **kwargs)
    except Exception:
        return None


def load_theme(theme_path: str | None = None, brand_description: str | None = None) -> Theme:
    """Resolve a Theme: explicit file → brand description (LLM-inferred) →
    bundled neutral default. `theme_path`/`brand_description` fall back to
    persisted config when not passed explicitly."""
    from . import config

    path = theme_path or config.get("theme_path")
    if path:
        p = Path(path).expanduser()
        if p.is_dir():
            for name in ("theme.yaml", "theme.yml", "theme.json"):
                if (p / name).exists():
                    return _load_theme_file(p / name)
            raise FileNotFoundError(f"No theme.yaml/theme.json found in {p}")
        if p.exists():
            return _load_theme_file(p)
        raise FileNotFoundError(f"Theme not found: {p}")

    desc = brand_description or config.get("brand_description")
    if desc:
        inferred = _infer_theme(desc)
        if inferred:
            return inferred

    return DEFAULT_THEME
