# Sample case library

Three invented cases used in pandoro's own tests, docs, and demos — no real
client data. See [`CASE_LIBRARY_SCHEMA.md`](../../CASE_LIBRARY_SCHEMA.md)
for the format.

Try it:

```bash
pandoro deck-mixer list --library deck_mixer/examples/sample-library
pandoro deck-mixer build reference --library deck_mixer/examples/sample-library --cases northwind-retail-support
pandoro deck-mixer build capabilities --library deck_mixer/examples/sample-library
pandoro deck-mixer build tender --library deck_mixer/examples/sample-library --tender-tags "human in the loop"
```

`templates/case.md` is the starting point for a new case — copy it into
`cases/{your-slug}/case.md` and fill it in, or run
`pandoro deck-mixer library init <path>` to scaffold a fresh library with the same
template.
