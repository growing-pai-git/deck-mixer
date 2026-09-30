# Architecture

Repo-wide architecture home for Pandoro. Each tool now keeps its own
architecture-as-code inside its own folder rather than under here — see
[`deck_mixer/architecture/`](../deck_mixer/architecture/README.md),
modelled with [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML).

## Conventions (for a tool's own `architecture/` folder)

- One `!include`-able `.puml` file per diagram, grouped by C4 level: `context/`,
  `containers/`, `components/`, `dynamic/`.
- `_shared/c4_version.puml` pins the C4-PlantUML stdlib to a release tag (not
  `master`) — bump it there to upgrade every diagram at once.
- `Templates/` holds a blank skeleton for the smallest reusable unit in that
  tool (e.g. one module) so new ones start from the same shape.
- Rendered output (`.png`/`.svg`/`.pdf`) is gitignored — regenerate from source
  with the PlantUML CLI/extension, don't commit images.

See also [`pandoro-high-level.drawio`](pandoro-high-level.drawio) for a
single-page, non-C4 overview — quicker to scan, easier to hand to someone who
just wants the shape of the system.
