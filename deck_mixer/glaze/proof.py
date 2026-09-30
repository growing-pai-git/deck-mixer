"""Glaze · Phase 2 — Proof.

Decide which proposed placeholders actually earn their place. In baking,
proofing is letting the dough rest and *verifying it's ready*; here we verify
each placeholder genuinely enhances the deck before paying to fill it.

Rules (heuristic, deck-aware):
  - A placeholder with no usable spec/hint is rejected (e.g. diagram with no
    nodes, chart with no series).
  - Photo density is capped: at most ~60% of content slides may carry a photo
    (~30% when no image source is configured and slots become placeholders).
    When over budget, the lowest-priority photos are dropped first.
  - Background photos on statement slides are a luxury — only the strongest
    survive the cap.

Optional Claude scoring (ANTHROPIC_API_KEY) can refine priorities before the
cap is applied; absent a key the proposed priorities are used as-is.
"""

from __future__ import annotations

from ..theme import DEFAULT_THEME, Theme
from .placeholders import (
    SlidePlan, PHOTO, DIAGRAM, CHART, KPI, APPROVED, REJECTED,
)

# At most this fraction of content slides should carry a photo.
PHOTO_DENSITY_CAP = 0.60
# With no image source configured, the approved slots become placeholders the
# user fills by hand — keep those to a handful.
PLACEHOLDER_DENSITY_CAP = 0.30


def proof(slides: list[SlidePlan], theme: Theme = DEFAULT_THEME) -> list[SlidePlan]:
    """Phase 2: approve/reject placeholders across the whole deck.

    Runs structural validity first, then — when an LLM key is configured —
    lets it judge holistically whether each placeholder enhances the deck
    (adjusting priorities / dropping weak ones). The photo-density cap always
    applies afterwards as a hard ceiling.
    """
    # 1. Structural validity — reject placeholders that can't be filled well.
    for sp in slides:
        for ph in sp.placeholders:
            ok, why = _is_viable(ph)
            if not ok:
                ph.status = REJECTED
                ph.reason = why

    # 1b. LLM evaluation (under the hood; silent fallback to heuristics).
    from ..llm import available
    if available():
        _llm_evaluate(slides, theme)

    # 2. Photo-density budget across the deck. round() rather than floor() so
    # short decks (e.g. a 3-case tender deck) aren't cut to a single photo.
    from ..visuals import sources_available
    n_slides = max(1, len(slides))
    cap = PHOTO_DENSITY_CAP if sources_available() else PLACEHOLDER_DENSITY_CAP
    photo_budget = max(1, round(n_slides * cap))

    photo_phs = [
        ph for sp in slides for ph in sp.placeholders
        if ph.kind == PHOTO and ph.status != REJECTED
    ]
    # Highest priority first; keep within budget, reject the rest.
    photo_phs.sort(key=lambda p: p.priority, reverse=True)
    for i, ph in enumerate(photo_phs):
        if i < photo_budget:
            ph.status = APPROVED
            ph.reason = "within photo budget"
        else:
            ph.status = REJECTED
            ph.reason = "over photo-density budget"

    # 3. Non-photo placeholders that passed validity are approved outright.
    for sp in slides:
        for ph in sp.placeholders:
            if ph.kind != PHOTO and ph.status != REJECTED:
                ph.status = APPROVED
                ph.reason = ph.reason or "structural visual approved"

    return slides


def _llm_evaluate(slides: list[SlidePlan], theme: Theme = DEFAULT_THEME) -> None:
    """Let an LLM (Gemini, falling back to Claude) judge each still-viable
    placeholder against the deck content.

    Mutates placeholders in place: sets priority and rejects ones judged
    unhelpful. Silent no-op on any error (heuristics then carry the decision).
    """
    from ..llm import call_json

    # Build an index of evaluable placeholders (not already rejected).
    items = []
    for si, sp in enumerate(slides):
        for pi, ph in enumerate(sp.placeholders):
            if ph.status == REJECTED:
                continue
            items.append((si, pi, sp, ph))
    if not items:
        return

    schema = {
        "type": "object",
        "properties": {
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "placeholder id"},
                        "keep": {"type": "boolean"},
                        "priority": {"type": "number",
                                     "description": "0..1 — how much it helps"},
                        "medium": {
                            "type": "string",
                            "enum": ["generate", "photo"],
                            "description": (
                                "generate = AI image (default; best for abstract/"
                                "concept/background, on-brand); photo = real stock "
                                "photo (only when authenticity matters: real people, "
                                "places, client evidence)."),
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["id", "keep", "priority", "medium"],
                },
            }
        },
        "required": ["decisions"],
    }

    lines = []
    for idx, (_, _, sp, ph) in enumerate(items):
        bullets = " | ".join(sp.bullets[:3])
        lines.append(
            f"[{idx}] slide='{sp.headline}' layout={sp.layout} "
            f"visual={ph.kind}/{ph.role} hint='{ph.hint}' bullets='{bullets}'")
    prompt = (
        "For each candidate visual below, decide (a) whether it genuinely "
        "improves the deck and (b) its medium. Prefer restraint: data/"
        "architecture slides rarely need a photo; bold statements can benefit "
        "from an abstract backdrop; not every slide should carry an image. "
        "For medium, default to 'generate' (AI image, on-brand) for abstract, "
        "conceptual or background visuals; choose 'photo' only when real-world "
        "authenticity matters (actual people, places, or client evidence). "
        "Keep the strongest, drop filler.\n\n"
        + "\n".join(lines)
    )
    system = (f"You are the art director for {theme.company_name} decks. You "
              "decide which visuals earn their place — quality and restraint "
              "over decoration.")

    result = call_json(system, prompt, schema)
    if not result:
        return
    for d in result.get("decisions", []):
        i = d.get("id")
        if not isinstance(i, int) or not (0 <= i < len(items)):
            continue
        _, _, _, ph = items[i]
        if d.get("keep") is False:
            ph.status = REJECTED
            ph.reason = "LLM: " + (d.get("reason") or "not needed")
        else:
            ph.priority = float(d.get("priority", ph.priority))
            if d.get("medium") in ("generate", "photo"):
                ph.medium = d["medium"]
            ph.reason = "LLM: " + (d.get("reason") or "endorsed")


def _is_viable(ph) -> tuple[bool, str]:
    if ph.kind == DIAGRAM:
        if not (ph.spec or {}).get("nodes"):
            return False, "no diagram structure to render"
    elif ph.kind == CHART:
        spec = ph.spec or {}
        if not spec.get("categories") or not spec.get("series"):
            return False, "no chart data"
    elif ph.kind == KPI:
        if not (ph.spec or {}).get("metrics"):
            return False, "no metrics"
    elif ph.kind == PHOTO:
        if not ph.hint.strip():
            return False, "no photo query"
    return True, ""
