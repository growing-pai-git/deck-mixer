# Deck Mixer

Turn a library of Markdown case studies into branded, editable PowerPoint
decks — reference decks, capability overviews, tender decks, and free-form
plans. Add a free Gemini API key and an AI "art director" designs your slides
and generates its images; without keys it still runs, but the decks look
basic ([how to add keys](deck_mixer/README.md#api-keys--strongly-recommended)).

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
