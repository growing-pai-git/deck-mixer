# Pandoro Engine — Architecture

The engine that turns a bring-your-own case library and a bring-your-own
theme into a branded, editable PPTX deck — no case data or brand baked in.

Modelled with [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) instead of
freehand PlantUML — same toolchain, but `Person` / `System` / `Container` / `Component`
give this system's layers (CLI/MCP surface → planning → beautify pipeline → rendering)
proper semantics that a fragment-composed diagram doesn't.

## Layout

```
context/       System Context  — the engine, its user, and its external dependencies
containers/    Container       — CLI, MCP server, and every internal module
components/    Component       — one file per module with internal structure worth showing
dynamic/       Dynamic         — the build-a-deck sequence, CLI/MCP through to the .pptx
Templates/     Skeleton for adding a new module's component diagram
_shared/       Pins the C4-PlantUML stdlib version every diagram includes
```

Render any file with the PlantUML CLI/extension. Each diagram includes
`_shared/c4_version.puml` then `!includeurl`s the C4-PlantUML macros it needs — the
stdlib is pinned to a release tag there, not `master`, so every diagram upgrades
together with a one-line change instead of drifting silently.

## Two things are always bring-your-own

Every diagram in this folder treats these as external systems, never as engine
internals — see [`../CASE_LIBRARY_SCHEMA.md`](../CASE_LIBRARY_SCHEMA.md)
and [`../theme.py`](../theme.py):

- **Case Library** — a folder of Markdown cases + `catalog.json`.
- **Brand Theme** — a `theme.yaml` + assets, or a free-text description, or
  nothing (a neutral default).

## Modules

| Module | Responsibility |
|---|---|
| CLI (`cli.py`) | `pandoro build / list / library / theme / mcp / configure / skill` |
| MCP Server (`server.py`) | The same operations as MCP tools, over stdio |
| Config (`config.py`) | env var → `~/.config/pandoro/keys.json` → default resolution |
| Case Library Reader (`kb.py`) | Loads/filters cases from the library |
| Theme Resolver (`theme.py`) | Loads/infers/defaults the active `Theme` |
| Art Director (`planner.py`) | AI-assisted slide-structure planning |
| Glaze Pipeline (`glaze/`) | Plan → Fetch → Place: layout, imagery, placement — see `components/glaze_pipeline.puml` |
| Deck Builder (`builder.py`) | Assembles the final `python-pptx` Presentation |
| Diagram/Chart Renderers (`diagrams.py`, `charts.py`) | Native diagram/chart slides |
| LLM Gateway (`llm.py`) | Provider-registry text/JSON calls — see `components/llm_gateway.puml` |
| Image Gateway (`imagegen.py`, `images.py`) | Provider-registry generation + stock fallback — see `components/image_gateway.puml` |

## Zero-API-key path is first-class

Every AI-assisted step has a non-AI fallback: `planner.py` and `glaze/recipe.py`
degrade to layout heuristics, image slots degrade to marked placeholders
the user replaces with their own pictures — no network calls. A deck always builds — richer with keys, never
blocked without them. See `context/context_diagram.puml` and `dynamic/build_deck_flow.puml`.

## Related

- [`../../architecture/pandoro-high-level.drawio`](../../architecture/pandoro-high-level.drawio) — a single-page,
  non-C4 overview of the same system.
