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

Never invent library content or brand colors — ask. To demo the tool before
they have a library, use the three invented sample cases bundled with this
skill (`SAMPLE_LIBRARY`, printed by setup; also the default when `--library`
is omitted). Say they are made-up examples.

## Starting from scratch (no library yet)

Plenty of first-time users have never written a case up before. Don't hand
them raw commands — walk them through it:

1. Scaffold the folder: `pandoro deck-mixer library init /path/to/new-library`.
   This writes `templates/case.md`, a fill-in-the-blanks template.
2. Ask about one real project at a time (client, what was done, the result)
   and draft `cases/<slug>/case.md` for them from the template — don't ask
   them to write markdown by hand. The field list and all 13 required
   sections are in
   `vendor/pandoro-src/deck_mixer/CASE_LIBRARY_SCHEMA.md`;
   `validate` (next step) rejects a case with fewer than 13 sections, but a
   section can be a single honest sentence — a rough first pass beats
   waiting for every field to be polished.
3. Run `pandoro deck-mixer library validate /path/to/new-library`
   and fix anything it flags before building.
4. Three or four cases is enough to build a first deck — don't insist on a
   complete library before showing them a result.

## Setting up a theme

If they already have brand colors, either write them a `theme.yaml`
(`pandoro deck-mixer theme init /path --company "..."`,
then edit the hex codes) or just pass `--brand-description "..."` inline —
no file needed. If they have no opinion yet, build with no theme at all; the
neutral default is a real, presentable option, not a placeholder to apologize
for.

## Setup

Run once per environment, from this skill's folder (safe to re-run):

```bash
python3 setup.py        # Windows: py setup.py
```

This installs `pandoro` into a local `.venv` from the copy of the engine
bundled inside this skill (`vendor/pandoro-src/`) — no GitHub access needed;
`pip` downloads the dependencies from PyPI. It prints two lines to reuse:

- `PANDORO=...` — the full path of the command. **Every `pandoro` in the
  examples below means this path** — never a bare `pandoro`, which may be a
  different install or missing.
- `SAMPLE_LIBRARY=...` — the bundled sample cases.

If setup fails while downloading packages in a sandbox, its network settings
probably block PyPI: tell the user, don't retry in a loop.

## Where you are running

**Claude Code (the user's own machine):** you can read their files directly.
Ask for the path to their case library, build into a folder they choose, and
tell them where the `.pptx` landed.

**Claude chat (claude.ai or Claude Desktop, code-execution sandbox):** the
sandbox cannot see the user's computer, and it is wiped when the chat ends.

- Ask them to upload their case library as a `.zip` (or the individual
  `case.md` files). Unzip it into a working folder and run
  `pandoro deck-mixer library validate` on it before building.
- Save decks with `--output-dir` pointing to the folder whose files are
  offered to the user as downloads (for example `/mnt/user-data/outputs`
  when it exists), and hand over the file.
- If you add or edit cases for them, give the updated library back as a
  `.zip` — otherwise the changes are lost with the sandbox.
- Setup runs again in every new chat; that's expected.

## Always start by looking at the library

Never guess a case slug. List first, pick from what comes back:

```bash
pandoro deck-mixer list --library /path/to/their-library
pandoro deck-mixer list --library /path/to/their-library --capabilities RAG --exclude-confidential
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
pandoro deck-mixer build reference --library /path/to/lib \
    --cases acme-rag-onboarding other-case-slug \
    --theme /path/to/theme.yaml

# Portfolio overview, grouped by capability (or --group-by tender_tags)
pandoro deck-mixer build capabilities --library /path/to/lib --exclude-confidential

# Tender — the brief lands on slide 2 and frames the whole deck
pandoro deck-mixer build tender --library /path/to/lib \
    --tender-tags governance "human in the loop" \
    --brief "Tender context in one or two sentences." \
    --exclude-confidential

# From a markdown outline — each '## ' heading becomes a slide
pandoro deck-mixer build plan --title "Plan of Approach" \
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

## API keys — make sure the user has them

Without keys, decks look basic: rule-based layouts and grey image
placeholders. Keys are what make them good — an AI "art director" designs the
slides (**text**) and pictures are generated for them (**images**). Before the
first deck, check whether keys are set (`pandoro deck-mixer configure` lists
them) and, if not, tell the user plainly what they're missing and recommend
at least one text key and one image key. The easiest answer is one free
Gemini key, which covers both: https://aistudio.google.com/apikey

| Key | Text | Images |
|---|---|---|
| `GEMINI_API_KEY` (recommended, free tier) | ✓ | ✓ |
| `OPENAI_API_KEY` | ✓ | ✓ |
| `ANTHROPIC_API_KEY` | ✓ | — |
| `STABILITY_API_KEY` / `TOGETHER_API_KEY` / `FAL_KEY` / `REPLICATE_API_TOKEN` | — | ✓ |
| `PEXELS_API_KEY` / `UNSPLASH_ACCESS_KEY` | — | stock photos |

How to add them depends on where you run:

- **Claude Code:** ask the user to run
  `pandoro deck-mixer configure --gemini-api-key <key>` in their own terminal
  (outside this chat; saved to `~/.config/pandoro/keys.json`, owner-only), or
  to set the environment variable in their shell profile. Then build.
- **Claude chat sandbox:** keys are forgotten when the chat ends. Explain the
  choice: for AI-designed decks every time, the Deck Mixer extension for
  Claude Desktop (keys in the OS keychain) or Claude Code is the better home;
  or they can give you a key for this chat only — it then stays in the chat
  history, so suggest a separate key they can delete afterwards. Pass it as an
  environment variable on the build command; never write it to a file you
  hand back.

If they still choose to go without, build the deck — and when you deliver it,
say in one line that it's the basic version and a key would add AI layouts
and images. Don't hide the build's "built without AI keys" warning.

## Delivering the result

The command prints the path to the generated `.pptx`. Give the user the
file. Then say which cases went in, so they can sanity-check the selection
before it goes to a client.

## What this skill cannot do

There is no add/remove command: a case is just a `cases/<slug>/case.md`
file. To capture a new case, draft that file from the template (see
[Starting from scratch](#starting-from-scratch-no-library-yet)), save it in
their library (Claude Code) or hand back the updated library zip (chat), and
run `library validate`. Only delete a case when the user explicitly asks.
