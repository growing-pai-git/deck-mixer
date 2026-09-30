---
name: deck-mixer
description: Build branded PowerPoint decks from a case-study library — reference decks for specific client cases, capabilities/portfolio overviews, tender decks answering an RFP, and plan/proposal decks from a markdown outline. Use whenever someone asks for a deck, slides, a presentation, references for a client, or a plan of approach.
---

# Pandoro

Turns a case-study library into branded `.pptx` decks. This skill packs the
engine only — it ships with **no case data and no brand baked in**. Before
building anything, you need to know two things from the user (or their repo):

1. **Where is their case library?** A folder following `CASE_LIBRARY_SCHEMA.md`
   (ask, or look for one in the current project — commonly `cases/` or
   `kb/` with a `catalog.json` at its root). If they don't have one yet,
   see [Starting from scratch](#starting-from-scratch-no-library-yet) below.
2. **Do they have a brand/theme?** A `theme.yaml`/`theme.json` (`--theme`), or
   describe the brand in a sentence (`--brand-description`), or omit both for
   a clean neutral default — that default is a perfectly good place to start,
   don't block on this.

Never invent library content or brand colors — ask, or use the sample
library at `deck_mixer/examples/sample-library` (bundled with the pandoro
repo, not this skill) purely to demo the tool.

## Starting from scratch (no library yet)

Plenty of first-time users have never written a case up before. Don't hand
them raw commands — walk them through it:

1. Scaffold the folder: `.venv/bin/pandoro deck-mixer library init /path/to/new-library`.
   This writes `templates/case.md`, a fill-in-the-blanks template.
2. Ask about one real project at a time (client, what was done, the result)
   and draft `cases/<slug>/case.md` for them from the template — don't ask
   them to write markdown by hand. The field list and all 13 required
   sections are in
   `vendor/pandoro-src/deck_mixer/CASE_LIBRARY_SCHEMA.md`;
   `validate` (next step) rejects a case with fewer than 13 sections, but a
   section can be a single honest sentence — a rough first pass beats
   waiting for every field to be polished.
3. Run `.venv/bin/pandoro deck-mixer library validate /path/to/new-library`
   and fix anything it flags before building.
4. Three or four cases is enough to build a first deck — don't insist on a
   complete library before showing them a result.

## Setting up a theme

If they already have brand colors, either write them a `theme.yaml`
(`.venv/bin/pandoro deck-mixer theme init /path --company "..."`,
then edit the hex codes) or just pass `--brand-description "..."` inline —
no file needed. If they have no opinion yet, build with no theme at all; the
neutral default is a real, presentable option, not a placeholder to apologize
for.

## Setup

Run once (idempotent):

```bash
bash setup.sh
```

This installs `pandoro` into a local `.venv` from the copy of the engine
bundled inside this skill (`vendor/pandoro-src/`) — no PyPI, no GitHub access,
and no network needed beyond what `pip` needs for its own dependencies. Use
`.venv/bin/pandoro` for every command below — not a bare `pandoro`, in case
the system Python is externally managed.

## Always start by looking at the library

Never guess a case slug. List first, pick from what comes back:

```bash
.venv/bin/pandoro deck-mixer list --library /path/to/their-library
.venv/bin/pandoro deck-mixer list --library /path/to/their-library --capabilities RAG --exclude-confidential
```

Use the `slug` values from the output in the build commands below.

## Choosing the deck type

| The user is asking for | Command |
|---|---|
| Specific cases — "our work for Acme", "references for X" | `build reference` |
| Breadth — "what we do", portfolio, capability overview | `build capabilities` |
| A response to an RFP or tender | `build tender` |
| A deck from a document, plan, or proposal they wrote | `build plan` |

If it's genuinely ambiguous, ask — a tender deck and a capabilities deck
answer very different questions, and rebuilding is cheap but not free.

```bash
# Specific cases
.venv/bin/pandoro deck-mixer build reference --library /path/to/lib \
    --cases acme-rag-onboarding other-case-slug \
    --theme /path/to/theme.yaml

# Portfolio overview, grouped by capability (or --group-by tender_tags)
.venv/bin/pandoro deck-mixer build capabilities --library /path/to/lib --exclude-confidential

# Tender — the brief lands on slide 2 and frames the whole deck
.venv/bin/pandoro deck-mixer build tender --library /path/to/lib \
    --tender-tags governance "human in the loop" \
    --brief "Tender context in one or two sentences." \
    --exclude-confidential

# From a markdown outline — each '## ' heading becomes a slide
.venv/bin/pandoro deck-mixer build plan --title "Plan of Approach" \
    --content outline.md --company "Client Name"
```

Add `--filename my-deck` to control the output name, and `--output-dir` to
control where it's written; otherwise the filename is timestamped and it
lands in the current directory.

## Rules that matter

**Confidentiality.** Pass `--exclude-confidential` on anything that leaves
the organization — tender submissions, prospect meetings, public talks.
Cases are marked in the catalog and there is no way to un-send a deck. When
in doubt about the audience, ask who will see it.

**The tender brief is worth getting right.** Ask the user for the tender
context in a sentence or two before building; `--brief` shapes slide 2,
which is the slide that makes the deck feel written for that RFP rather than
generic.

**Pick 3–6 cases for a tender.** Filtering by tag can return the whole
library; a deck with twelve evidence slides doesn't get read. Narrow it, and
say which cases you chose and why.

## API keys are optional

Decks build with no keys at all — layout heuristics, with marked image placeholders where pictures would go. Setting
one of these unlocks better output:

- `GEMINI_API_KEY` — best single key: AI slide-layout planning *and* image
  generation (free at aistudio.google.com)
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — layout planning
- `PEXELS_API_KEY` / `UNSPLASH_ACCESS_KEY` — stock photography

Save them with `.venv/bin/pandoro deck-mixer configure --gemini-api-key ...` so they
persist across runs. If a user wants richer decks, point them at a free
Gemini key. Don't block on it.

## Delivering the result

The command prints the path to the generated `.pptx`. Give the user the
file. Then say which cases went in, so they can sanity-check the selection
before it goes to a client.

## What this skill cannot do

It reads a case library; it does not manage one. Adding or removing cases is
a `library`-folder operation (or, via the MCP server, the `add_case`/
`remove_case` tools) — not something this CLI skill does for you. If a user
wants a new case captured, offer to draft the case markdown for them to add.
