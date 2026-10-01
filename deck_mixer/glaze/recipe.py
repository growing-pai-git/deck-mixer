"""Glaze · Phase 1 — Recipe.

Turn raw document sections into SlidePlans, each annotated with typed
placeholders (the spots that *could* be enriched). This phase only proposes;
the Proof phase decides what stays.

Uses the planner (Claude when available, heuristics otherwise) for the layout
brain, then derives placeholders from the chosen layout.
"""

from __future__ import annotations

from ..theme import DEFAULT_THEME, Theme
from .placeholders import (
    Placeholder, SlidePlan,
    PHOTO, DIAGRAM, CHART, KPI,
    BACKGROUND, SPLIT, FULL,
    GENERATE, PHOTO_REAL,
)

# Subjects where a real photo beats AI generation (authenticity matters).
_PHOTO_SUBJECTS = (
    "team", "mensen", "people", "klant", "client", "portret", "portrait",
    "kantoor", "office", "samenwerking", "collaboration", "handen", "hands",
    "stad", "city", "gebouw", "building", "fabriek", "factory", "winkel",
    "store", "publiek", "audience", "medewerker", "employee",
)


def _pick_medium(hint: str, role: str) -> str:
    """Default to AI generation; use a real photo only for authentic subjects."""
    low = hint.lower()
    if role != BACKGROUND and any(w in low for w in _PHOTO_SUBJECTS):
        return PHOTO_REAL
    return GENERATE


def make_recipe(sections: list[tuple[str, str]], company: str = "",
                layouts: tuple | None = None, theme: Theme = DEFAULT_THEME,
                slide_plan: list[dict] | None = None) -> list[SlidePlan]:
    """Phase 1: produce SlidePlans with proposed placeholders.

    `layouts` restricts which layout choices the planner may pick — pass a
    subset when the caller can't back every layout with real data.
    `slide_plan` is a caller-supplied plan (already run through
    planner.validate_plan); when given, the planner is skipped.
    """
    from ..planner import plan_deck, LAYOUTS

    planned = plan_deck(sections, company=company, layouts=layouts or LAYOUTS, theme=theme,
                        plan=slide_plan)
    slides: list[SlidePlan] = []

    for (heading, body), p in zip(sections, planned):
        layout = p.get("layout", "bullets")
        # Statement/quote slides show one line; anything longer would be lost
        # to the speaker notes, whoever planned it.
        if layout in ("statement", "quote") and not is_short_section(body):
            layout = "bullets"
        sp = SlidePlan(
            section_heading=heading,
            layout=layout,
            headline=p.get("headline") or heading,
            bullets=p.get("bullets") or [],
            notes=p.get("speaker_notes", ""),
            lead=p.get("lead", ""),
        )
        _attach_placeholders(sp, p, body)
        slides.append(sp)

    return slides


def is_short_section(body: str) -> bool:
    """A section small enough to stand as a one-idea statement slide."""
    from ..kb import extract_bullets, strip_markdown
    return len(extract_bullets(body, 5)) <= 1 and len(strip_markdown(body)) <= 160


# Each image-bearing layout defines how the picture must be composed so it
# FITS the slot: (placeholder role, orientation, composition guidance).
_LAYOUT_IMAGE = {
    "image_right": (SPLIT, "portrait",
                    "the main subject framed toward the LEFT, with soft open "
                    "negative space on the right"),
    "image_left":  (SPLIT, "portrait",
                    "the main subject framed toward the RIGHT, with soft open "
                    "negative space on the left"),
    "image_full":  (BACKGROUND, "landscape",
                    "a wide cinematic composition with a calm, uncluttered band "
                    "along the bottom third for a caption"),
    "statement":   (BACKGROUND, "landscape",
                    "an atmospheric wide composition with a calm, uncluttered "
                    "centre where a short headline can sit"),
}


def _attach_placeholders(sp: SlidePlan, plan: dict, body: str) -> None:
    visual = plan.get("visual") or {}

    # Image demand from the Plan step, composed to fit the chosen layout.
    spec = _LAYOUT_IMAGE.get(sp.layout)
    wants_image = visual.get("want") and (spec is not None or sp.layout == "bullets")
    if wants_image:
        if spec is None:                    # a "bullets" slide that wants an image
            sp.layout = "image_right"
            spec = _LAYOUT_IMAGE["image_right"]
        role, orientation, composition = spec
        brief = (visual.get("brief") or "").strip()
        hint = brief.split(";")[0].split(".")[0].strip() or sp.headline
        medium = visual.get("medium") or _pick_medium(hint, role)
        priority = 0.7 if role == SPLIT else 0.5
        sp.placeholders.append(Placeholder(
            kind=PHOTO, role=role, hint=hint, brief=brief,
            composition=composition, orientation=orientation,
            medium=medium, priority=priority))

    if sp.layout == "diagram":
        spec = plan.get("diagram")
        sp.placeholders.append(Placeholder(
            kind=DIAGRAM, role=FULL, hint=sp.headline,
            spec=spec or {}, priority=0.85))

    elif sp.layout == "chart":
        sp.placeholders.append(Placeholder(
            kind=CHART, role=FULL, hint=sp.headline,
            spec=plan.get("chart", {}), priority=0.85))

    elif sp.layout == "kpi":
        sp.placeholders.append(Placeholder(
            kind=KPI, role=FULL, hint=sp.headline,
            spec={"metrics": plan.get("metrics", [])}, priority=0.8))

    # "bullets" and "quote" carry no placeholder — they are clean by design.
