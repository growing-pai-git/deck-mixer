"""Deck planner — the 'art director' step.

Reads a document's storyline (its sections) and decides, per slide, the
layout and visual treatment: which slides are clean information, which get a
photo, which become a bold statement, which carry a diagram, etc.

Where the plan comes from, in order: a plan supplied by the caller (e.g.
Claude, via create_plan_deck's slide_plan — checked by validate_plan), else an
LLM when a key is set, else deterministic heuristics so decks still get
varied, sensible layouts.

Each planned slide:
    {
      "layout": one of LAYOUTS,
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

# The design judgement behind every plan. Used verbatim in the internal
# planner's prompt AND in create_plan_deck's slide_plan description, so a plan
# from the LLM planner and a plan from Claude follow the same rules.
DESIGN_RULES = (
    "DESIGN a varied, beautiful slide deck — each slide's layout should suit its "
    "own content, and the deck as a whole should have rhythm. Hard rules: never "
    "use the same layout on two consecutive slides; alternate image_left and "
    "image_right; reserve image_full and statement for emphasis (at most ~1 in 4 "
    "slides each); statement and quote show one short line, so use them only for "
    "a section with a single idea; put dense detail on clean bullet slides. "
    "For EACH slide, decide the visual demand: set visual.want true only where "
    "an image genuinely strengthens the message, and when true write a vivid "
    "one-sentence brief DESCRIBING the image to create — its subject, "
    "composition and mood — connected to that slide's point and the overall "
    "storyline, not a search query. Prefer AI-generated imagery "
    "(medium=generate); choose photo only for authentic people/places. "
    "Restraint reads as premium — not every slide needs a visual."
)

# Layouts a caller-supplied plan may use: the ones that need no extra data.
# (diagram/chart/kpi need a structured spec the internal planner derives.)
PLAN_LAYOUTS = ("statement", "bullets", "quote", "image_left", "image_right", "image_full")


def _build_system(theme: Theme) -> str:
    return (
        f"You are the art director for {theme.company_name}. "
        "Given a document's sections, " + DESIGN_RULES + " "
        "Use diagram/chart/kpi when the content is structural or numeric, and "
        "never put an image on those. "
        f"Theme to honour: {', '.join(theme.mood)}; a {theme.palette_description} "
        "palette; clean, premium, lots of negative space."
    )


def plan_deck(sections: list[tuple[str, str]], company: str = "",
              layouts: tuple = LAYOUTS, theme: Theme = DEFAULT_THEME,
              plan: list[dict] | None = None) -> list[dict]:
    """Return a per-section plan — one entry per section, given the OBJECTIVE
    of that section, choosing whichever layout best serves it. Uses an LLM
    when a key is configured; otherwise a varied heuristic rotation.

    `layouts` restricts which layout choices are offered — pass a subset when
    the caller can't back every layout with real data (e.g. no quotes/charts).
    """
    if plan is not None:            # supplied by the caller, already validated
        return plan
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


# --- Caller-supplied plans (e.g. Claude via create_plan_deck) ---------------

_VISUAL_ROLE = {"image_left": "split", "image_right": "split",
                "image_full": "background", "statement": "background"}


def _norm(heading: str) -> str:
    return " ".join(str(heading).split()).casefold()


def _text(value, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def validate_plan(sections: list[tuple[str, str]], slide_plan,
                  theme: Theme = DEFAULT_THEME) -> tuple[list[dict], list[str]]:
    """Turn a caller's slide_plan into a complete, safe plan for `sections`.

    Entries join to sections on their `heading`. Anything missing or invalid
    falls back to the heuristic plan for that slide only, and each fallback is
    described in the returned fixes so the caller can correct and resend.
    """
    from .glaze.recipe import is_short_section

    fixes: list[str] = []
    entries = slide_plan.get("slides") if isinstance(slide_plan, dict) else slide_plan
    if not isinstance(entries, list):
        fixes.append("slide_plan is not a list of slides; used the built-in layouts")
        entries = []

    by_heading: dict[str, dict] = {}
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not _text(entry.get("heading"), 200):
            fixes.append(f"slide_plan entry {i}: no heading, ignored")
            continue
        key = _norm(entry["heading"])
        if key in by_heading:
            fixes.append(f"slide_plan entry {i}: heading '{entry['heading']}' repeats, kept the first")
            continue
        by_heading[key] = entry
    known = {_norm(h) for h, _ in sections}
    for key, entry in by_heading.items():
        if key not in known:
            fixes.append(f"'{entry['heading']}' matches no '## ' heading in the content, ignored")

    plan: list[dict] = []
    for idx, (heading, body) in enumerate(sections):
        n = idx + 1
        fallback = _heuristic_slide(heading, body, idx, PLAN_LAYOUTS, theme)
        entry = by_heading.get(_norm(heading))
        if entry is None:
            fixes.append(f"slide {n} '{heading}': not in slide_plan, "
                         f"used the built-in layout ({fallback['layout']})")
            plan.append(fallback)
            continue

        layout = _text(entry.get("layout"), 40)
        if layout not in PLAN_LAYOUTS:
            fixes.append(f"slide {n} '{heading}': layout '{layout}' is not one of "
                         f"{', '.join(PLAN_LAYOUTS)}; used {fallback['layout']}")
            layout = fallback["layout"]
        elif layout in ("statement", "quote") and not is_short_section(body):
            fixes.append(f"slide {n} '{heading}': too much content for a {layout} slide; "
                         "used bullets (or shorten the section)")
            layout = "bullets"

        bullets = entry.get("bullets")
        if isinstance(bullets, list):
            bullets = [b for b in (_text(x, 300) for x in bullets) if b][:6]
        else:
            if bullets is not None:
                fixes.append(f"slide {n} '{heading}': bullets must be a list of strings; "
                             "used the content's own bullets")
            bullets = fallback["bullets"]

        visual = entry.get("visual")
        if isinstance(visual, dict) and visual.get("want") is True:
            medium = visual.get("medium") if visual.get("medium") in ("generate", "photo") else "generate"
            vis = {"want": True, "role": _VISUAL_ROLE.get(layout, "split"), "medium": medium,
                   "brief": _text(visual.get("brief"), 400)}
            if not vis["brief"]:
                fixes.append(f"slide {n} '{heading}': visual.want without a brief; "
                             "the image will be described from the headline")
        else:
            vis = {"want": False, "role": "split", "medium": "generate", "brief": ""}

        plan.append({
            "layout": layout,
            "headline": _text(entry.get("headline"), 120) or heading,
            "bullets": bullets,
            "lead": fallback["lead"],
            "speaker_notes": _text(entry.get("speaker_notes"), 3000) or fallback["speaker_notes"],
            "visual": vis,
        })
    return plan, fixes


def describe_plan(sections: list[tuple[str, str]], plan: list[dict]) -> list[dict]:
    """The plan as a caller sees and edits it: the slide_plan format."""
    return [{"heading": heading, "layout": p.get("layout"), "headline": p.get("headline"),
             "bullets": p.get("bullets") or [], "visual": p.get("visual")}
            for (heading, _), p in zip(sections, plan)]


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
