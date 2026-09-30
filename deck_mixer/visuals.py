"""Unified visual resolver.

One entry point every deck builder uses to obtain a slide image, so behaviour
is consistent everywhere: try AI generation first (the configured provider),
fall back to stock photos, and shape both with the deck's style.

    resolve_image("procesautomatisatie", role="split")  ->  JPEG/PNG bytes | None
"""

from __future__ import annotations

from .glaze.style import DeckStyle, BRAND_STYLE
from .glaze.placeholders import SPLIT, GENERATE, PHOTO_REAL


def resolve_image(hint: str, role: str = SPLIT, *, medium: str = GENERATE,
                  brief: str = "", composition: str = "", orientation: str = "",
                  style: DeckStyle | None = None) -> bytes | None:
    """Return image bytes for a slot, honouring medium, layout fit and style.

    `brief` drives AI generation (storyline); `composition` + `orientation`
    make the image fit the slide's layout; `hint` is the short stock query.

    generate: AI image (brief-led, layout-fit prompt) → stock photo fallback.
    photo:    stock photo (style query) → AI image fallback.
    """
    import os
    from .imagegen import generate_image
    from .images import fetch_image

    style = style or BRAND_STYLE
    orient = orientation or style.orientation(role)

    def gen():
        return generate_image(
            style.gen_prompt(hint, role, brief=brief, composition=composition), orient)

    def photo():
        return fetch_image(style.query(hint, role), orient)

    prefer_gen = (os.environ.get("IMAGE_PREFER_GENERATE") or "").strip().lower() \
        in ("1", "true", "yes", "on")

    try:
        if medium == PHOTO_REAL and not prefer_gen:
            return photo() or gen()
        return gen() or photo()
    except Exception:
        return None


def sources_available() -> bool:
    """True when at least one image source (AI generation or keyed stock
    photos) is configured. Without one, decks get image placeholders."""
    from .imagegen import configured_providers
    from .images import configured
    return bool(configured_providers() or configured())


def visuals_status() -> str:
    """Human-readable summary of what image sources are live."""
    from .imagegen import configured_providers, active_provider
    from .images import configured

    gen = configured_providers()
    active = active_provider()
    photo = configured()

    lines = []
    if gen:
        lines.append(f"AI generation: {', '.join(gen)} (active: {active})")
    else:
        lines.append("AI generation: none configured")
    lines.append(f"Stock photos: {', '.join(photo) or 'none configured'}")
    if not gen and not photo:
        lines.append("Decks get image placeholders to replace with your own pictures.")
    return "\n".join(lines)
