"""Glaze · Phase 3 — Place.

Decide where each filled visual belongs on its slide. This turns an abstract
"this slide has an approved background photo" into a concrete region the
builder renders into, and keeps the layout honest (e.g. a split image only
counts if it actually came back).

Regions:
    background — full-bleed behind a statement, under a dark scrim
    left/right — the image column beside bullets
    fullbleed  — the whole slide, caption band along the bottom
    full       — the slide's main content area (diagram / chart / kpi)
    none       — no visual; render the slide clean

An image slot that was approved but didn't come back (no image source
configured, or every source failed) keeps its column and is rendered as a
marked placeholder for the user to fill — `Placement.hint` says what goes there.
"""

from __future__ import annotations

from .placeholders import (
    SlidePlan, Placement, PHOTO, DIAGRAM, CHART, KPI, BACKGROUND, REJECTED,
)


def place(slides: list[SlidePlan]) -> list[SlidePlan]:
    """Phase 3: set each slide's placement from its filled visuals + layout."""
    for sp in slides:
        sp.placement = _placement_for(sp)
    return slides


def _placement_for(sp: SlidePlan) -> Placement:
    # Structural visuals own the main area.
    if sp.filled(DIAGRAM):
        return Placement("full", "diagram")
    if sp.filled(CHART):
        return Placement("full", "chart")
    if sp.filled(KPI):
        return Placement("full", "kpi")

    photo = sp.filled(PHOTO)
    if photo:
        if sp.layout == "image_full":
            return Placement("fullbleed", "full-bleed image")
        if sp.layout == "image_left":
            return Placement("left", "image left")
        if sp.layout == "image_right":
            return Placement("right", "image right")
        if photo.role == BACKGROUND:
            return Placement("background", "statement backdrop")
        return Placement("right", "split image")

    # An approved image slot that wasn't filled becomes a placeholder column.
    # A full-bleed placeholder would hide the text, so it moves to the side.
    wanted = next((ph for ph in sp.placeholders
                   if ph.kind == PHOTO and ph.status != REJECTED), None)
    if wanted and sp.layout in ("image_left", "image_right", "image_full"):
        if sp.layout == "image_full":
            sp.layout = "image_right"
        side = "left" if sp.layout == "image_left" else "right"
        return Placement(side, "image placeholder", hint=wanted.hint)

    # No image wanted — collapse to a clean layout so the builder doesn't
    # reserve an empty image area.
    if sp.layout in ("image_left", "image_right", "image_full"):
        sp.layout = "bullets"
    return Placement("none", "clean")
