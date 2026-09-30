"""Make text fit its box.

python-pptx can't measure rendered text, so this estimates it: greedy word
wrap against an average glyph width, then line height from the font size and
line spacing. The estimate is deliberately a little pessimistic — a box that
ends up slightly under-full looks fine; text spilling past the footer does not.

    size, text = fit_text(body, width, height, max_size=15, min_size=11)

Shrinks the font first; if the text still doesn't fit at `min_size`, drops
whole sentences from the end (never cutting mid-word) and adds an ellipsis.
"""

from __future__ import annotations

import re

EMU_PER_PT = 12700

# Average advance width as a fraction of the font size. Calibri/Arial body
# text measures ~0.47–0.50em; bold and all-caps run wider.
CHAR_W = 0.52
CHAR_W_BOLD = 0.56

# Default text-box insets (0.1" left/right, 0.05" top/bottom), in points.
INSET_X_PT = 14.4
INSET_Y_PT = 7.2


def _wrapped_lines(paragraph: str, chars_per_line: int) -> int:
    if not paragraph.strip():
        return 1
    lines, used = 1, 0
    for word in paragraph.split():
        n = len(word)
        if used == 0:
            used = n
        elif used + 1 + n <= chars_per_line:
            used += 1 + n
        else:
            lines += 1
            used = n
        while used > chars_per_line:            # a single word longer than a line
            lines += 1
            used -= chars_per_line
    return lines


def text_height(paragraphs: list[str], width, size: float, *, line_spacing: float = 1.2,
                para_gap_pt: float = 0.0, bold: bool = False) -> float:
    """Estimated height in EMU of `paragraphs` set at `size` pt in a box `width` EMU wide."""
    usable_pt = max(1.0, width / EMU_PER_PT - INSET_X_PT)
    cpl = max(1, int(usable_pt / (size * (CHAR_W_BOLD if bold else CHAR_W))))
    lines = sum(_wrapped_lines(p, cpl) for p in paragraphs)
    gaps = para_gap_pt * max(0, len(paragraphs) - 1)
    return int((lines * size * 1.2 * line_spacing + gaps + INSET_Y_PT) * EMU_PER_PT)


def fits(paragraphs: list[str], width, height, size: float, **kw) -> bool:
    return text_height(paragraphs, width, size, **kw) <= height


def fit_size(paragraphs: list[str], width, height, max_size: float, min_size: float,
             **kw) -> float | None:
    """Largest whole point size in [min_size, max_size] that fits, else None."""
    size = max_size
    while size >= min_size:
        if fits(paragraphs, width, height, size, **kw):
            return size
        size -= 1
    return None


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s]


def fit_text(text: str, width, height, max_size: float, min_size: float,
             **kw) -> tuple[float, str]:
    """Return (size, text) such that text fits the box. Paragraphs are
    separated by newlines. Trims whole sentences from the end as a last resort."""
    paragraphs = text.split("\n")
    size = fit_size(paragraphs, width, height, max_size, min_size, **kw)
    if size is not None:
        return size, text

    # Too long even at min_size: keep as many leading sentences as fit.
    kept: list[str] = []
    for para in paragraphs:
        current = ""
        for sentence in _sentences(para) or [para]:
            trial = f"{current} {sentence}".strip()
            if not fits(kept + [trial + "…"], width, height, min_size, **kw):
                if current or kept:
                    return min_size, _ellipsis("\n".join(kept + [current]).strip())
                return min_size, _fit_words(sentence, width, height, min_size, **kw)
            current = trial
        kept.append(current)
    return min_size, "\n".join(kept)


def _fit_words(sentence: str, width, height, size: float, **kw) -> str:
    """A single sentence too long for the box: keep as many words as fit."""
    words: list[str] = []
    for w in sentence.split():
        if not fits([" ".join(words + [w]) + "…"], width, height, size, **kw):
            break
        words.append(w)
    return _ellipsis(" ".join(words))


# Space before each bullet after the first, as a fraction of the font size.
BULLET_GAP_EM = 0.9


def fit_bullets(bullets: list[str], width, height, max_size: float, min_size: float,
                *, marker: str = "—   ", **kw) -> tuple[float, list[str]]:
    """Return (size, bullets) that fit, shrinking the font before dropping
    trailing bullets."""
    items = list(bullets)
    while items:
        paragraphs = [marker + b for b in items]
        size = max_size
        while size >= min_size:
            if fits(paragraphs, width, height, size, para_gap_pt=size * BULLET_GAP_EM, **kw):
                return size, items
            size -= 1
        if len(items) == 1:
            _, text = fit_text(marker + items[0], width, height, min_size, min_size, **kw)
            return min_size, [text[len(marker):] if text.startswith(marker) else text]
        items.pop()
    return max_size, []


def _ellipsis(text: str) -> str:
    text = text.rstrip()
    return text if text.endswith("…") else text.rstrip(".,;:") + "…"
