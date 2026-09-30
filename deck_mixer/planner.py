"""Deck planner — the 'art director' step.

Reads a document's storyline (its sections) and decides, per slide, the
layout and visual treatment: which slides are clean information, which get a
photo, which become a bold statement, which carry a diagram, etc.

Uses Claude (tool use) when ANTHROPIC_API_KEY is set; otherwise falls back to
deterministic heuristics so decks still get varied, sensible layouts.

Each planned slide:
    {
      "layout": "statement|bullets|photo_split|quote|diagram",
      "headline": str,
      "bullets": [str, ...],
      "speaker_notes": str,
      "visual": {                     # the visual DEMAND for this slide
        "want": bool,
        "role": "background|split",
        "medium": "generate|photo",
        "brief": str,                 # rich description, following the storyline
      },
    }
"""

from __future__ import annotations

from .theme import DEFAULT_THEME, Theme

LAYOUTS = ("statement", "bullets", "quote", "diagram", "chart", "kpi",
           "image_left", "image_right", "image_full")

_LAYOUT_DESCRIPTION = (
    "Choose the layout that best fits THIS slide's content; "
    "vary it across the deck for rhythm. "
    "statement = one bold idea on colour, no bullets (openings/"
    "transitions/key messages); "
    "bullets = clean information, no image; "
    "image_left / image_right = bullets with a supporting image "
    "on that side (alternate the side between slides); "
    "image_full = full-bleed image with a short caption band "
    "(use sparingly, for emphasis or emotive moments); "
    "quote = a single pulled quote; "
    "diagram = a process/architecture; "
    "chart = comparable numbers; kpi = a few headline metrics."
)


def _build_tool(layouts: tuple) -> dict:
    return {
        "name": "deck_plan",
        "description": "A planned slide deck: one entry per content section, with "
                       "a chosen layout and visual treatment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "slides": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "layout": {
                                "type": "string",
                                "enum": list(layouts),
                                "description": _LAYOUT_DESCRIPTION,
                            },
                            "headline": {"type": "string", "description": "Punchy, <= 9 words"},
                            "bullets": {
                                "type": "array", "items": {"type": "string"},
                                "description": "3-5 crisp bullets (omit for statement/quote)",
                            },
                            "speaker_notes": {"type": "string"},
                            "visual": {
                                "type": "object",
                                "description": "The visual DEMAND for this slide.",
                                "properties": {
                                    "want": {"type": "boolean",
                                             "description": "Does this slide genuinely want an image?"},
                                    "role": {"type": "string", "enum": ["background", "split"],
                                             "description": "background = full-bleed behind a "
                                                            "statement; split = beside bullets."},
                                    "medium": {"type": "string", "enum": ["generate", "photo"],
                                               "description": "generate = AI image (abstract/"
                                                              "concept, default); photo = real "
                                                              "stock photo (authentic people/places)."},
                                    "brief": {"type": "string",
                                              "description": (
                                                  "One vivid sentence DESCRIBING the image to make, "
                                                  "tied to this slide's message and the deck's "
                                                  "storyline. Describe subject, composition and "
                                                  "mood — not a search query. Empty if want=false.")},
                                },
                                "required": ["want", "role", "medium", "brief"],
                            },
                        },
                        "required": ["layout", "headline", "speaker_notes", "visual"],
                    },
                }
            },
            "required": ["slides"],
        },
    }

def _build_system(theme: Theme) -> str:
    return (
        f"You are the art director for {theme.company_name}. "
        "Given a document's sections, DESIGN a varied, beautiful slide deck — each "
        "slide's layout should suit its own content, and the deck as a whole should "
        "have rhythm. Hard rules: never use the same layout on two consecutive "
        "slides; alternate image_left and image_right; reserve image_full and "
        "statement for emphasis (at most ~1 in 4 slides each); put dense detail on "
        "clean bullet slides; use diagram/chart/kpi when the content is structural "
        "or numeric. "
        "For EACH slide, decide the visual demand: set visual.want true only where "
        "an image genuinely strengthens the message (never on data/diagram slides), "
        "and when true write a vivid one-sentence brief DESCRIBING the image to "
        "create — its subject, composition and mood — connected to that slide's "
        f"point and the overall storyline. Theme to honour: {', '.join(theme.mood)}; "
        f"a {theme.palette_description} palette; clean, premium, lots of "
        "negative space. Prefer AI-generated abstract imagery; choose photo only "
        "for authentic people/places. Restraint reads as premium — not every slide "
        "needs a visual."
    )


def plan_deck(sections: list[tuple[str, str]], company: str = "",
              layouts: tuple = LAYOUTS, theme: Theme = DEFAULT_THEME) -> list[dict]:
    """Return a per-section plan — one entry per section, given the OBJECTIVE
    of that section, choosing whichever layout best serves it. Uses an LLM
    when a key is configured; otherwise a varied heuristic rotation.

    `layouts` restricts which layout choices are offered — pass a subset when
    the caller can't back every layout with real data (e.g. no quotes/charts).
    """
    from .llm import call_json

    system = _build_system(theme)
    if set(layouts) != set(LAYOUTS):
        system += f" For this deck, ONLY choose a layout from: {', '.join(layouts)}."
    system += (
        f" CRITICAL: return EXACTLY {len(sections)} slide plans, one per "
        "section given below, in the same order. Never split one section "
        "into multiple slides and never merge sections together."
    )
    doc = "\n\n".join(f"## {h}\n{b[:1200]}" for h, b in sections)
    ctx = f"Client: {company}.\n\n" if company else ""
    user = f"{ctx}Plan a deck for these sections:\n\n{doc}"

    result = call_json(system, user, _build_tool(layouts)["input_schema"])
    plan = result.get("slides") if result else None
    if plan and len(plan) == len(sections):
        return plan
    return [_heuristic_slide(h, b, i, layouts, theme) for i, (h, b) in enumerate(sections)]


# --- Heuristic fallback ----------------------------------------------------

_DIAGRAM_HINTS = ("architectuur", "flow", "pipeline", "proces", "stappen",
                  "aanpak", "architecture", "workflow")
_PHOTO_HINTS = ("team", "mensen", "klant", "samenwerking", "visie", "context",
                "cultuur", "adoptie", "people", "vision")


# A varied rotation used when content gives no stronger signal — keeps
# adjacent slides from sharing a layout and alternates image sides.
_ROTATION = ("image_right", "bullets", "image_left", "statement",
             "image_right", "bullets", "image_left")


def _heuristic_slide(heading: str, body: str, idx: int, layouts: tuple = LAYOUTS,
                     theme: Theme = DEFAULT_THEME) -> dict:
    from .kb import extract_bullets, split_lead, strip_markdown
    bullets = extract_bullets(body, 5)
    lead = split_lead(body)
    note = strip_markdown(body)[:600]
    no_visual = {"want": False, "role": "split", "medium": "generate", "brief": ""}
    allowed = set(layouts)
    rotation = tuple(l for l in _ROTATION if l in allowed) or ("bullets",)

    def out(layout, role=None):
        vis = _visual_demand(heading, role, theme) if role else no_visual
        return {"layout": layout, "headline": heading, "bullets": bullets, "lead": lead,
                "speaker_notes": note, "visual": vis}

    # Note: free-form plan decks have no diagram structure to render, so the
    # heuristic never picks "diagram" (that layout is driven by case frontmatter
    # in reference decks). Variety here comes from the rotation.
    from .glaze.recipe import is_short_section
    short = is_short_section(body)
    if idx == 0 and short and "statement" in allowed:   # bold opener
        return out("statement", "background")

    base = rotation[idx % len(rotation)]
    # Don't put a content-heavy slide on statement — it would drop the content.
    if base == "statement" and not short:
        base = "image_left" if (idx % 2 and "image_left" in allowed) else "image_right"
        if base not in allowed:
            base = "bullets"

    if base == "bullets":
        return out("bullets")
    if base == "statement":
        return out("statement", "background")
    return out(base, "split")                       # image_left / image_right


def _visual_demand(heading: str, role: str, theme: Theme = DEFAULT_THEME) -> dict:
    """Compose a visual demand + descriptive brief from a heading."""
    h = heading.lower()
    palette = theme.palette_description
    if any(w in h for w in ("team", "mensen", "samenwerking", "cultuur", "adoptie")):
        return {"want": True, "role": role, "medium": "photo",
                "brief": f"A diverse team collaborating in a bright modern office, "
                         f"conveying {heading.lower()}; candid, optimistic, premium."}
    if any(w in h for w in ("visie", "strategie", "toekomst", "vision")):
        return {"want": True, "role": role, "medium": "generate",
                "brief": f"An abstract forward-looking composition evoking {heading.lower()} "
                         f"— ascending geometric forms, {palette}, lots of space."}
    if any(w in h for w in ("data", "analyse", "inzicht", "resultaat")):
        return {"want": True, "role": role, "medium": "generate",
                "brief": f"A clean abstract data-flow visualisation suggesting {heading.lower()}, "
                         f"glowing nodes and lines, {palette}, minimal."}
    return {"want": True, "role": role, "medium": "generate",
            "brief": f"A premium abstract illustration representing {heading.lower()} in a "
                     f"business context; {palette}, soft gradients, lots of space."}
