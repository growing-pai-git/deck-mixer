"""Glaze · deck style profile.

A single DeckStyle is computed once per deck and threaded through every source
call, so all fetched visuals share one consistent look — the "style and spirit"
of the deck. It shapes image queries (mood + palette + subject bias) and the
orientation requested per placeholder role.

Anchored to the active Theme's palette/mood by default; an LLM can refine the
mood per deck (subject bias, adjectives) when a key is present, but the
palette always stays theme-anchored so decks remain on-brand.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..theme import DEFAULT_THEME, Theme
from .placeholders import BACKGROUND, SPLIT, FULL


def _cfg(key: str) -> str:
    """Read an image-style preference (env → keys.json), '' if unset."""
    from ..config import get
    return (get(key) or "").strip()


@dataclass
class DeckStyle:
    mood: list[str] = field(default_factory=lambda: list(DEFAULT_THEME.mood))
    palette: str = DEFAULT_THEME.palette_description
    subject_bias: str = DEFAULT_THEME.subject_bias
    # negative cues kept out of queries (documented intent)
    avoid: str = "no text, no logos, no watermark"
    # optional creative overrides (config-driven, read per deck)
    theme: str = field(default_factory=lambda: _cfg("image_theme"))
    art_style: str = field(default_factory=lambda: _cfg("image_art_style"))

    def query(self, hint: str, role: str = SPLIT) -> str:
        """Compose a stock-photo search query that carries the deck's look."""
        bits = [hint.strip()] if hint.strip() else []
        # role nuance: backgrounds favour abstract, splits favour real scenes
        if role == BACKGROUND:
            bits.append("abstract")
        bits.append(", ".join(self.mood[:2]))
        bits.append(self.palette)
        return ", ".join(b for b in bits if b)

    def gen_prompt(self, hint: str, role: str = SPLIT, brief: str = "",
                   composition: str = "") -> str:
        """Compose a generation prompt — on-brand, no text, layout-aware.

        `brief` (the Plan step's description) leads so the image follows the
        storyline; `composition` makes it FIT the slide's layout (where to leave
        negative space). The deck theme and guardrails are always appended.
        """
        if brief.strip():
            subject = brief.strip().rstrip(".")
        else:
            base = hint.strip() or self.subject_bias
            form = ("a sleek abstract background composition representing"
                    if role == BACKGROUND else
                    "a clean modern editorial illustration of")
            subject = f"{form} {base}"
        if self.theme:
            subject = f"{subject}, reimagined within a {self.theme} setting"
        comp = f" Compose with {composition}." if composition.strip() else \
               " Lots of negative space."
        if self.art_style:
            # A chosen art style leads the look (overrides the palette default).
            look = f"{self.art_style}, rich and characterful, soft warm light"
        else:
            look = (f"{', '.join(self.mood)} style, {self.palette}, premium, "
                    f"soft depth, flat subtle gradients")
        return (
            f"{subject}. {look}.{comp} "
            f"Absolutely no text anywhere in the image: no words, letters, "
            f"numbers, signage, labels, captions, logos or charts."
        )

    def orientation(self, role: str) -> str:
        return "landscape" if role in (BACKGROUND, FULL) else "portrait"


def _theme_style(theme: Theme) -> DeckStyle:
    return DeckStyle(
        mood=list(theme.mood),
        palette=theme.palette_description,
        subject_bias=theme.subject_bias,
        art_style=theme.art_style or _cfg("image_art_style"),
    )


# The default style — used whenever no theme/LLM tuning is available.
BRAND_STYLE = DeckStyle()


def infer_style(sections: list[tuple[str, str]], company: str = "",
                theme: Theme = DEFAULT_THEME) -> DeckStyle:
    """Optionally tune the mood/subject bias to the deck's spirit via an LLM.

    Always returns a DeckStyle; falls back to the theme's own style without a
    key or on any error. The palette stays anchored to the active Theme so
    decks remain recognisably on-brand; only the mood/subject bias adapt.
    """
    base = _theme_style(theme)

    from ..llm import available, call_json
    if not available():
        return base

    schema = {
        "type": "object",
        "properties": {
            "mood": {"type": "array", "items": {"type": "string"},
                     "description": "3-4 adjectives for the imagery's feel "
                                    "(e.g. approachable, civic; or sleek, technical)"},
            "subject_bias": {"type": "string",
                             "description": "2-3 words for preferred subjects "
                                            "(e.g. 'public sector people', 'data centers')"},
        },
        "required": ["mood", "subject_bias"],
    }
    head = "\n".join(h for h, _ in sections)
    ctx = f"Client: {company}. " if company else ""
    system = (f"You set the visual mood for a {theme.company_name} deck. The "
              f"palette is fixed ({theme.palette_description}); choose a mood "
              "and subject bias that match the deck's spirit.")

    data = call_json(system, f"{ctx}Deck sections:\n{head}", schema)
    if data:
        return DeckStyle(
            mood=data.get("mood") or base.mood,
            palette=base.palette,  # keep theme anchor
            subject_bias=data.get("subject_bias") or base.subject_bias,
            art_style=base.art_style,
        )
    return base
