"""Core data model for the Glaze engine.

A deck is described as a list of SlidePlans. Each slide carries typed
Placeholders — the spots that *could* be visually enriched. Placeholders flow
through three phases:

    Recipe (plan)  -> status "proposed"
    Proof  (eval)  -> status "approved" | "rejected"
    Pour   (fill)  -> status "filled"   | "failed"
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Placeholder kinds
PHOTO   = "photo"
DIAGRAM = "diagram"
CHART   = "chart"
KPI     = "kpi"

# Roles — how the visual sits on the slide
BACKGROUND = "background"   # full-bleed behind text (statement slides)
SPLIT      = "split"        # beside the text (photo_split)
FULL       = "full"         # the slide's main content (diagram/chart)

PROPOSED = "proposed"
APPROVED = "approved"
REJECTED = "rejected"
FILLED   = "filled"
FAILED   = "failed"

# Medium for image placeholders — how the picture is produced.
GENERATE = "generate"   # AI-generated, on-brand (default for most)
PHOTO_REAL = "photo"    # real stock photo (only when authenticity matters)


@dataclass
class Placeholder:
    kind: str                       # PHOTO | DIAGRAM | CHART | KPI
    role: str                       # BACKGROUND | SPLIT | FULL
    hint: str = ""                  # short search query (stock photos)
    brief: str = ""                 # rich description of the wanted visual,
                                    # following the storyline + deck theme
    composition: str = ""           # layout-aware framing (where to leave space)
    orientation: str = ""           # landscape | portrait | square (slot aspect)
    spec: dict = field(default_factory=dict)   # structured spec (chart/diagram/kpi)
    priority: float = 0.5           # 0..1 — how much it would help
    medium: str = GENERATE          # GENERATE | PHOTO_REAL (photo placeholders only)
    status: str = PROPOSED
    reason: str = ""                # why approved / rejected
    content: object = None          # filled result: image bytes, or a spec dict

    @property
    def is_approved(self) -> bool:
        return self.status in (APPROVED, FILLED)

    @property
    def is_filled(self) -> bool:
        return self.status == FILLED and self.content is not None


@dataclass
class Placement:
    """Where a filled visual belongs on the slide (the Place step output)."""
    region: str = "none"            # none | background | left | right | fullbleed | full
    note: str = ""
    hint: str = ""                  # what belongs in an unfilled image slot


@dataclass
class SlidePlan:
    section_heading: str
    layout: str                     # statement | bullets | photo_split | quote | diagram | chart | kpi
    headline: str
    bullets: list[str] = field(default_factory=list)
    notes: str = ""
    lead: str = ""                  # intro prose shown above the bullets (heuristic plans)
    placeholders: list[Placeholder] = field(default_factory=list)
    placement: Placement = field(default_factory=Placement)

    def approved(self, kind: str | None = None) -> list[Placeholder]:
        return [p for p in self.placeholders
                if p.is_approved and (kind is None or p.kind == kind)]

    def filled(self, kind: str | None = None) -> Placeholder | None:
        for p in self.placeholders:
            if p.is_filled and (kind is None or p.kind == kind):
                return p
        return None
