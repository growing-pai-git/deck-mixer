# Deck Mixer

Turn a library of Markdown case studies into branded, editable PowerPoint
decks — reference decks, capability overviews, tender decks, and free-form
plans. Works with zero API keys; add one to let an AI "art director" plan
each slide's layout and imagery.

Made by [Growing pAI](https://growingpai.com). Installs as the `pandoro`
command: every Deck Mixer command is `pandoro deck-mixer ...`.

```bash
pip install -e .          # from a checkout, for now
pandoro deck-mixer build capabilities --library deck_mixer/examples/sample-library
```

- **[README](deck_mixer/README.md)** — features, CLI reference, theming, MCP server, Claude Skill.
- **[HOWTO](deck_mixer/HOWTO.md)** — beginner-friendly, step-by-step guide.
- **[Case library schema](deck_mixer/CASE_LIBRARY_SCHEMA.md)** — the format your cases follow.

## Development

```bash
pip install -e ".[dev]"
pytest deck_mixer/tests/
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT — see [`LICENSE`](LICENSE).
