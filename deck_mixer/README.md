# Pandoro

Turn a case-study library into branded, editable PowerPoint decks.

New to the command line? See [`HOWTO.md`](HOWTO.md) for a beginner-friendly,
step-by-step guide. This README assumes some familiarity with a terminal.

Point pandoro at a folder of Markdown case studies and it generates
reference, capabilities, tender, or free-form plan decks — with an AI "art
director" choosing each slide's layout and imagery from what that slide
actually needs to say, not a fixed template. Every slide is built natively
in `python-pptx` (real editable text, charts, and diagrams — no rasterized
images), so the output opens and edits like any other deck.

Both the case library and the brand are bring-your-own:

- **Case library** — any folder following [`CASE_LIBRARY_SCHEMA.md`](CASE_LIBRARY_SCHEMA.md).
  No case data ships with pandoro; try [`examples/sample-library`](examples/sample-library)
  for a working example.
- **Theme** — an explicit `theme.yaml`/`theme.json` + logo/favicon, a free-text
  brand description (colors/mood inferred by an LLM), or nothing at all (a
  tasteful neutral default). Optionally a corporate `.pptx`/`.potx` template
  (`--template`) for its masters.

## What you can count on

- **Nothing overflows.** Every text box is fitted to its space: the font
  shrinks within a readable range first, and only then are whole trailing
  sentences or bullets dropped (never mid-word). Full text stays in the
  speaker notes.
- **Confidential stays confidential.** Cases marked `confidential` are shown
  by sector, and the client's name (plus any `aliases`) is replaced with
  "the client" in titles, body text and notes.
- **No surprise pictures.** Images come only from sources you configure (AI
  generation or Pexels/Unsplash keys). Without one, image slots become clearly
  marked placeholders — a grey frame with a suggestion of what belongs there,
  grouped so it deletes in one click.
- **Clean files.** Proper document properties (title, author = your company),
  no leftover "Click to add title" boxes, all shapes editable.

The closing slide carries a small "Made with Deck Mixer by Growing pAI"
line; set `credit: false` in your `theme.yaml` to remove it.

## Install

```bash
pip install -e .          # from a checkout, for now
```

## Quickstart

```bash
# Explore the bundled sample library
pandoro deck-mixer list --library deck_mixer/examples/sample-library

# Build decks — works with zero API keys (layout heuristics, image placeholders)
pandoro deck-mixer build reference --library deck_mixer/examples/sample-library --cases northwind-retail-support
pandoro deck-mixer build capabilities --library deck_mixer/examples/sample-library
pandoro deck-mixer build tender --library deck_mixer/examples/sample-library --tender-tags "human in the loop"
pandoro deck-mixer build plan --title "Q1 Plan" --content my-plan.md

# Point at your own library and theme
pandoro deck-mixer build reference --library ~/my-cases --theme ~/my-brand/theme.yaml --cases some-case
```

Add API keys to unlock AI planning and imagery (works with zero keys too —
each key just unlocks more):

```bash
pandoro deck-mixer configure --gemini-api-key AIza...   # one free key covers planning + images
```

## Case library

```bash
pandoro deck-mixer library init ~/my-cases        # scaffold a new library
pandoro deck-mixer library validate ~/my-cases    # lint it against the schema
```

See [`CASE_LIBRARY_SCHEMA.md`](CASE_LIBRARY_SCHEMA.md) for the full format.

## Theme

```bash
pandoro deck-mixer theme init ~/my-brand --company "Acme Corp"   # tagline optional
# or infer a palette from a description (requires an LLM key):
pandoro deck-mixer theme init ~/my-brand --describe "a playful fintech startup, coral and navy"
```

The generated `theme.yaml` lists every option with a short comment; drop a
`logo.png` and `favicon.png` next to it. See [`theme.py`](theme.py) for the full list.

## MCP server

Deck-mixer also runs as an MCP server, so Claude Desktop/Code (or any MCP
client) can browse your library and build decks conversationally:

```json
{
  "mcpServers": {
    "deck-mixer": {
      "command": "pandoro",
      "args": ["deck-mixer", "mcp", "serve"],
      "cwd": "/absolute/path/to/your-case-library"
    }
  }
}
```

or `pandoro deck-mixer mcp serve` directly.

## Development

```bash
pip install -e ".[dev]"
pytest deck_mixer/tests/
```

See [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## License

MIT — see [`LICENSE`](../LICENSE).
