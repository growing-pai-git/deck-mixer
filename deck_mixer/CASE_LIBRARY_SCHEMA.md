# CASE_LIBRARY_SCHEMA.md — Pandoro Case Library Format

This file specifies the on-disk format pandoro expects when you point it at
`--library <path>` (or `library_path` / `LIBRARY_PATH`). Any folder that
follows this contract works — pandoro ships with no case data of its own.

---

## 1. What a case library is

A case library is a folder of Markdown "case studies" plus a generated JSON
index. It serves two audiences:

- **Humans**: browse cases, add new ones, use them to build decks.
- **Pandoro itself**: filter, retrieve, and extract structured content to
  build slides.

The `cases/` folder is the source of truth. `catalog.json` is a
machine-readable index generated from it — pandoro (`kb.rebuild_catalog`)
regenerates it whenever a case is added, merged, or removed, so you should
never hand-edit `catalog.json`.

## 2. Repository structure

```
your-library/
├── catalog.json              # Generated index — pandoro reads this first
├── cases/
│   └── {slug}/
│       └── case.md           # One directory per case
└── templates/
    └── case.md                # Optional: template for new cases
```

`pandoro library init <path>` scaffolds this structure for you.

## 3. `catalog.json` structure

```json
{
  "schema_version": "1.0",
  "generated_at": "<ISO 8601 UTC timestamp>",
  "total_cases": 1,
  "cases": [
    {
      "case_id": "acme-2026-rag-onboarding",
      "slug": "acme-rag-onboarding",
      "file_path": "cases/acme-rag-onboarding/case.md",
      "title": "...",
      "client": "...",
      "sector": "...",
      "client_type": "enterprise",
      "period": "...",
      "status": "production",
      "confidentiality": "public",
      "budget_order": "...",
      "effort_order": "...",
      "contact_person": "...",
      "last_updated": "2026-06-15",
      "technologies": ["..."],
      "capabilities": ["..."],
      "tender_tags": ["..."],
      "reusable_for": ["..."],
      "sections": ["1. Summary", "..."],
      "summary": "<first paragraph of section 1>"
    }
  ]
}
```

Run `pandoro library validate <path>` to rebuild and lint the catalog against
this schema; it reports missing frontmatter, broken section numbering, or
cases referenced in `catalog.json` with no matching file.

## 4. Field definitions

### Identification

| Field          | Type   | Description                                          |
|----------------|--------|-------------------------------------------------------|
| `case_id`      | string | Unique identifier, e.g. `acme-2026-rag-onboarding`.    |
| `slug`         | string | Directory name under `cases/`, URL-safe.               |
| `file_path`    | string | Relative path from the library root to the case file.  |
| `last_updated` | date   | ISO date of last edit (`YYYY-MM-DD`).                   |

### Client & context

| Field         | Type   | Suggested values                                    | Description               |
|---------------|--------|-------------------------------------------------------|----------------------------|
| `title`       | string | —                                                       | Full descriptive title.    |
| `client`      | string | —                                                       | Client name (may be anonymized). |
| `aliases`     | list   | —                                                       | Other names the client goes by in the text (e.g. `[Contoso, CMS]`). Redacted along with `client` for confidential cases. |
| `sector`      | string | —                                                       | Industry or domain.        |
| `client_type` | enum   | `sme`, `enterprise`, `public`, `regulated`, `other`     | Organization size/type.    |
| `period`      | string | —                                                       | Date range or duration.    |

### Status

Free text, but pandoro's slide/grouping logic looks for substrings like
`poc`, `pilot`, `production` — pick values that contain one of those when you
want that behaviour (e.g. `production ongoing`, `poc — client testing`).

### Confidentiality

| Value           | Meaning                                    | Effect on generated decks                         |
|------------------|---------------------------------------------|-----------------------------------------------------|
| `public`         | Freely shareable                            | Client name used freely.                            |
| `anonymized`     | Shareable, but not by client name           | Client name replaced with `sector` on slides.       |
| `confidential`   | Internal only                                | Excluded when a tool call sets `exclude_confidential=true`. Otherwise shown by `sector`; `client`, its `aliases` and the name without a legal suffix (e.g. "Contoso" for "Contoso Manufacturing") become "the client" in titles, text and notes. |

Any other string is treated as shareable (not `confidential`).

### Sizing

| Field           | Type   | Description                                             |
|-----------------|--------|-----------------------------------------------------------|
| `budget_order`  | string | Approximate project budget (e.g. `50k EUR`, `100+ days`). |
| `effort_order`  | string | Approximate effort (e.g. `~40 person-days`).               |
| `contact_person`| string | Client-side contact name and/or email.                     |

### Classification arrays

| Field          | Type          | Description                                                |
|----------------|---------------|--------------------------------------------------------------|
| `technologies` | list[string]  | Tools, platforms, frameworks used.                            |
| `capabilities` | list[string]  | Functional capabilities of the solution.                      |
| `tender_tags`  | list[string]  | Keywords for tender matching and positioning.                 |
| `reusable_for` | list[string]  | Analogous contexts where this case pattern could apply.       |

### Optional visual data (frontmatter)

These unlock native, editable slide visuals instead of plain bullets:

```yaml
metrics:
  - { value: "80%", label: "order emails automated" }
  - { value: "2000+", label: "documents per month" }
chart:
  type: column
  title: Order email processing
  categories: [Manual, Automated]
  series:
    Share of order emails: [20, 80]
diagram:
  type: flow
  caption: "Order emails are read, enriched and validated before reaching the ERP."
  nodes:
    - { id: mail, label: "Mailbox\norders" }
    - { id: llm,  label: "Model API\n+ matching", accent: true }
    - { id: erp,  label: "ERP" }
  edges:
    - [mail, llm]
    - [llm, erp]
```

`metrics` feeds a KPI-tile slide, `chart` a native PowerPoint chart, `diagram`
a native flow diagram (`nodes`/`edges`; `accent: true` highlights a node in
the theme's secondary colour). All three are optional — omit them and the
deck falls back to plain bullet slides built from the section text.

## 5. Case file structure

Each `cases/{slug}/case.md` has YAML frontmatter (the fields above) followed
by 13 standardized `## N. Title` sections. Section content can be written in
any language — pandoro's slide builders only key off the section *number*,
not the title text.

| #  | Section                                    | Primary use                                              |
|----|----------------------------------------------|-------------------------------------------------------------|
| 1  | Summary                                      | Executive summary; used directly on the summary slide.       |
| 2  | Client context                               | Background: size, sector, maturity.                          |
| 3  | Problem / challenge                          | Pain point: what was slow, manual, risky.                    |
| 4  | Objective                                    | What the client wanted to achieve.                            |
| 5  | Approach                                     | Methodology: workshops, co-creation, iterations.               |
| 6  | Solution                                     | Functional description of what was built.                     |
| 7  | Technology & architecture                    | Tech stack and design decisions.                               |
| 8  | Our role                                     | Your team's specific contributions.                            |
| 9  | Human in the loop, governance & quality      | Control, validation, auditability mechanisms.                  |
| 10 | Results & impact                             | Quantified outcomes (used on the results slide).               |
| 11 | Implementation & follow-up                   | Go-live, post-launch support, iteration.                        |
| 12 | Tender relevance                             | Why this case is a strong reference; used as speaker notes.    |
| 13 | Evidence & details                           | Factual metadata: client, period, budget, shareability.        |

To extract a specific section programmatically, match `^## {N}\. .*$`.

## 6. Section-to-slide mapping (reference decks)

| Slide                | Source section(s)     | Notes                                    |
|-----------------------|-------------------------|---------------------------------------------|
| Cover                 | `title`, `client`        | Anonymized if `confidentiality: confidential`. |
| Summary                | Section 1                | Used directly.                                |
| Context & Challenge     | Sections 2 + 3            | Two columns, prose.                           |
| Approach & Our Role      | Sections 5 + 8            | Methodology + your team's role.                |
| Solution                | Section 6                 | Functional, avoid heavy tech jargon.           |
| Tech Stack              | Section 7 + `technologies`| Chips rendered from the array.                 |
| Solution Architecture   | `diagram` (if present)    | Native diagram slide.                          |
| Results in Numbers      | `metrics` (if present)    | KPI tile slide.                                |
| Results & Impact        | Section 10 (+ `chart`)    | Native chart if present, else bullets.         |
| (speaker notes)         | Section 12                 | Tender positioning — not shown on slide.       |

## 7. Contributing a new case

1. Copy `templates/case.md` to `cases/{new-slug}/case.md` (or run
   `pandoro library init` in an existing library to get a fresh template).
2. Fill all frontmatter fields.
3. Write all 13 sections.
4. Set `last_updated` to today's date.
5. Run `pandoro library validate <path>` to rebuild `catalog.json` and check
   for errors.

Via the MCP server, `add_case` does steps 2-5 for you and checks for likely
duplicates first.

---

See `deck_mixer/examples/sample-library/` for a small, working library (three
invented cases) used in pandoro's own tests and docs.
