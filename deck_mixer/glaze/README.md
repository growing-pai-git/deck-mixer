# Glaze — the deck beautify engine

*A glaze is the glossy finishing coat that makes a pastry beautiful. This is
the finishing coat for decks.* Brandable display name: **Glacé**.

Glaze turns a storyline (document sections) into a beautiful deck in three
phases. Each slide carries typed **placeholders** — the spots that *could* be
enriched — and those placeholders flow through the phases.

```
sections ──▶ PLAN ──▶ FETCH ──▶ PLACE ──▶ SlidePlans (rendered by builder)
          demand+brief  get      put where
                        images   they belong
```

| Step | Module(s) | Responsibility |
|------|-----------|----------------|
| **1 · Plan** | `recipe.py` + `proof.py` (+ `../planner.py`) | For each slide decide the layout and the **visual demand**: does it want an image, and if so write a one-sentence **brief** DESCRIBING it, tied to the storyline and the deck theme. Then **evaluate** the demands — drop visuals that can't be filled (diagram w/o nodes, chart w/o data), let Claude judge which genuinely help (when a key is set), and apply a photo-density cap. |
| **2 · Fetch** | `pour.py` → `../visuals.py` | **Get the images.** The brief drives AI generation (selected provider); the short hint drives stock-photo search. Generation ↔ photo cross-fallback; runs in parallel; everything shaped by `DeckStyle`. |
| **3 · Place** | `place.py` | **Put each image where it belongs.** Sets each slide's `Placement.region` (`background` / `right` / `full` / `none`) from the filled visual's role + layout, and collapses a slide back to a clean layout when no image came back (no empty image columns). |

The brief is the heart of step 1 — it carries the *description* of the wanted
visual, not a bare search query, so generated imagery follows the narrative.

### Layout variety & image-fit

Step 1 also **designs each slide's layout** from its content and varies it for
rhythm (no two adjacent slides share a layout; image sides alternate;
`statement` / `image_full` are reserved for emphasis). The layout vocabulary:
`statement`, `bullets`, `image_left`, `image_right`, `image_full`, `quote`,
`diagram`, `chart`, `kpi`.

Because the layout is chosen *before* the image is made, each image demand
carries a **composition** ("subject on the right, negative space on the left…")
and an **orientation** matching its slot — so a generated image is framed to
sit correctly in that exact layout (portrait beside text, wide with a calm
caption band for full-bleed, etc.). Step 3 (Place) then drops it in the matching
region: `left` / `right` / `fullbleed` / `background`.

## Style (`style.py`)

A single `DeckStyle` is computed once per deck and threaded into every source
call — the "style and spirit" of the deck. The palette stays brand-anchored
(navy + orange); when a key is set, Claude tunes the *mood* to the deck's spirit
(e.g. civic & approachable vs. sleek & technical). `style.query(hint, role)`
composes the final search string; `style.orientation(role)` picks landscape vs.
portrait.

## Image medium — generate vs photo

Each image placeholder has a `medium`:

- **`generate`** (default, *most* slides) — AI-generated, on-brand imagery via
  `../imagegen.py`. Best for abstract / conceptual / background visuals.
- **`photo`** (only *when needed*) — a real stock photo, for authentic subjects
  (real people, places, client evidence).

Recipe sets a sensible default from the hint; when a key is present, **Claude
picks the medium per slide** during Proof. Pour resolves with cross-fallback:
`generate → photo` (or `photo → generate`) so a slide is never left empty.

## Source chains

AI generation (`../imagegen.py`):

```
OpenAI gpt-image-1  →  Stability AI core
(OPENAI_API_KEY)       (STABILITY_API_KEY)
```

Stock photos (`../images.py` · `fetch_image`):

```
Pexels  →  Unsplash
(key)      (key)
```

With no image key at all nothing is fetched: image slots render as clearly
marked placeholders (`slides.image_placeholder`) that you replace with your
own pictures — a deck never ships a random photo nobody chose.
Every query/prompt carries the deck's `DeckStyle`, so generated and stock
visuals share one look.

## Data model (`placeholders.py`)

- `Placeholder(kind, role, hint, spec, priority, status, content, reason)`
- `SlidePlan(section_heading, layout, headline, bullets, notes, placeholders)`

Status lifecycle: `proposed → approved | rejected → filled | failed`.

## Entry point

```python
from deck_mixer.glaze import glaze
slides = glaze(sections, company="Acme")   # fully poured SlidePlans
slides = glaze(sections, fill=False)        # stop after Proof (preview the plan)
```

## Tuning

- `proof.PHOTO_DENSITY_CAP` — max fraction of slides that may carry a photo (default 0.40).
- Placeholder `priority` set in `recipe.py` decides which photos survive the cap.
