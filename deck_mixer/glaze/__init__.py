"""Glaze — the deck beautify engine.

A glaze is the glossy finishing coat that makes a pastry beautiful; this engine
is the finishing coat for decks. It runs in three phases:

    Recipe  (recipe.make_recipe)  — plan slides; define typed placeholders
    Proof   (proof.proof)         — evaluate which placeholders earn their place
    Pour    (pour.pour)           — call sources to fill the approved ones

Brandable display name: "Glacé".

Usage:
    from deck_mixer.glaze import glaze
    slides = glaze(sections, company="Acme")   # -> list[SlidePlan], fully poured
"""

from __future__ import annotations

from ..theme import DEFAULT_THEME, Theme
from .placeholders import (        # noqa: F401  (re-exported for callers)
    Placeholder, SlidePlan,
    PHOTO, DIAGRAM, CHART, KPI,
    BACKGROUND, SPLIT, FULL,
    PROPOSED, APPROVED, REJECTED, FILLED, FAILED,
)
from .recipe import make_recipe
from .proof import proof
from .pour import pour
from .place import place
from .style import DeckStyle, infer_style

__all__ = ["glaze", "plan", "fetch", "place", "infer_style",
           "Placeholder", "SlidePlan", "DeckStyle"]


def plan(sections: list[tuple[str, str]], company: str = "",
         layouts: tuple | None = None, theme: Theme = DEFAULT_THEME,
         slide_plan: list[dict] | None = None) -> list[SlidePlan]:
    """Step 1 — Plan: build the storyline, DEMAND visuals and DESCRIBE them
    (each demanded image carries a brief), then evaluate which demands earn
    their place (an LLM when a key is set, heuristics otherwise).

    `layouts` restricts which layout choices are offered (see make_recipe)."""
    slides = make_recipe(sections, company=company, layouts=layouts, theme=theme,
                         slide_plan=slide_plan)
    return proof(slides, theme=theme)


def fetch(slides: list[SlidePlan], style: DeckStyle) -> list[SlidePlan]:
    """Step 2 — Glaze/fetch: get the actual images for every approved demand,
    using the brief (generation) / query (stock) and the deck style."""
    return pour(slides, style=style)


def glaze(sections: list[tuple[str, str]], company: str = "",
          fill: bool = True, style: DeckStyle | None = None,
          layouts: tuple | None = None, theme: Theme = DEFAULT_THEME,
          slide_plan: list[dict] | None = None) -> list[SlidePlan]:
    """Run the three Glaze steps and return finished SlidePlans.

        1. Plan   — demand + describe the visuals (recipe + proof)
        2. Fetch  — get the images (pour)
        3. Place  — put each image where it belongs (place)

    Args:
        sections: list of (heading, body) tuples — the storyline.
        company:  client name, for planning/style context.
        fill:     when False, stop after Plan (demands approved, not fetched).
        style:    DeckStyle to apply; when None it is inferred per deck
                  (LLM-tuned mood, theme palette as the anchor).
        layouts:  restrict which layouts the planner may choose (default: all).
        theme:    active Theme — supplies the palette/mood anchor and company
                  name used in planning prompts.
        slide_plan: a validated caller-supplied plan (planner.validate_plan);
                  skips the planner.
    """
    deck_style = style or infer_style(sections, company=company, theme=theme)
    slides = plan(sections, company=company, layouts=layouts, theme=theme,  # 1. demand + describe
                  slide_plan=slide_plan)
    if fill:
        slides = fetch(slides, deck_style)          # 2. get images
    slides = place(slides)                           # 3. place them
    return slides
