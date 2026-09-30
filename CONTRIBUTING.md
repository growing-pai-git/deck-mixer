# Contributing

Deck Mixer is designed to be forked, modified, and used as-is — no case
data or brand is baked in, so it should work for anyone's library and theme
out of the box. It ships as the `pandoro` Python package (`pandoro
deck-mixer ...`).

## Setup

```bash
git clone https://github.com/growing-pai-git/deck-mixer.git
cd deck-mixer
pip install -e ".[dev]"
pytest deck_mixer/tests/
```

The tests build every deck type from `deck_mixer/examples/sample-library`
with the default theme and zero API keys, so they run without any external
credentials.

## Project layout

- `pandoro/` — the umbrella package. `cli.py` is the thin dispatcher behind
  the `pandoro` console script; it registers each tool's subcommands.
- `deck_mixer/` — the deck-mixer tool: `kb.py` (case library),
  `theme.py` (branding), `builder.py`/`diagrams.py`/`charts.py` (slide
  rendering), `glaze/` (the planning pipeline — Recipe/Proof/Pour/Place),
  `planner.py`, `llm.py`, `imagegen.py`, `images.py` (visual sourcing),
  `cli.py` (registers the `pandoro deck-mixer` subcommands), `server.py`
  (MCP server), `skill_template/` (the shareable Claude Skill).
- `deck_mixer/examples/sample-library/` — three invented cases used in
  deck-mixer's tests and docs.
- `deck_mixer/CASE_LIBRARY_SCHEMA.md` — the case-library format
  contract.
- `deck_mixer/tests/` — deck-mixer's pytest suite.
- `mcpb/` — the Claude Desktop extension: `manifest.json`, the `main.py`
  entry point, and `build.py`, which packs `dist/deck-mixer-<version>.mcpb`.
  A new setting or MCP tool also goes into `manifest.json`
  (`test_mcpb.py` checks they match).

## Guidelines

- Keep the engine brand-agnostic: any hardcoded color, font, or copy string
  belongs on the `Theme` dataclass in `theme.py`, not inline in a slide
  factory. Every drawing function takes an explicit `theme: Theme` parameter.
- Keep the engine library-agnostic: nothing should assume a specific case
  library's content — only the documented `CASE_LIBRARY_SCHEMA.md` fields.
- New AI providers (planning or image generation) should follow the existing
  provider-registry pattern in `llm.py`/`imagegen.py` — one function per
  provider, gated on its own API key, registered in `_PROVIDERS`.
- Every feature should degrade gracefully with zero API keys configured
  (layout heuristics instead of AI planning, marked image placeholders
  instead of AI imagery) — that's the baseline experience, not a fallback
  path to neglect.

## Pull requests

Run `pytest deck_mixer/tests/` before opening a PR. If you change the case-library
schema or the `Theme` fields, update `deck_mixer/CASE_LIBRARY_SCHEMA.md` /
`deck_mixer/theme.py`'s docstring accordingly.
