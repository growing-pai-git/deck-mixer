"""Glaze · Phase 3 — Pour.

Fill every approved placeholder by calling its source. Photos hit the image
providers (AI generation, then Pexels → Unsplash); structural visuals (diagram/chart/kpi)
already carry their spec, so 'filling' just promotes the spec to content.

Photo fills run in parallel — pouring the glaze on every pastry at once.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .placeholders import (
    SlidePlan, PHOTO, DIAGRAM, CHART, KPI, FILLED, FAILED, APPROVED,
)
from .style import DeckStyle, BRAND_STYLE


def pour(slides: list[SlidePlan], style: DeckStyle | None = None,
         max_workers: int = 4) -> list[SlidePlan]:
    """Phase 3: resolve approved placeholders into concrete content.

    `style` shapes every photo query (mood + palette) and the requested
    orientation, so all fetched visuals share the deck's look.
    """
    style = style or BRAND_STYLE

    photo_phs = [
        ph for sp in slides for ph in sp.placeholders
        if ph.kind == PHOTO and ph.status == APPROVED
    ]

    # Structural visuals: spec -> content, no network.
    for sp in slides:
        for ph in sp.placeholders:
            if ph.status != APPROVED:
                continue
            if ph.kind in (DIAGRAM, CHART, KPI):
                ph.content = ph.spec
                ph.status = FILLED

    # Images: resolve each by medium (AI-generate vs real photo), in parallel.
    if photo_phs:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            jobs = [(ph, style) for ph in photo_phs]
            for ph, data in zip(photo_phs, pool.map(_resolve_image, jobs)):
                if data:
                    ph.content = data
                    ph.status = FILLED
                else:
                    ph.status = FAILED
                    ph.reason = "all sources returned nothing"

    return slides


def _resolve_image(job) -> bytes | None:
    """Fill one image placeholder via the shared resolver (gen ↔ photo)."""
    from ..visuals import resolve_image
    ph, style = job
    return resolve_image(ph.hint, ph.role, medium=ph.medium,
                         brief=ph.brief, composition=ph.composition,
                         orientation=ph.orientation, style=style)
