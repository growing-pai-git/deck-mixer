"""Case-library reader. See CASE_LIBRARY_SCHEMA.md for the on-disk format."""

import json
import re
from pathlib import Path


def load_catalog(kb_path: Path) -> dict:
    """The library's catalog, re-indexed first if any case.md is newer than
    catalog.json — so an edited case shows up without a manual rebuild."""
    catalog_file = kb_path / "catalog.json"
    case_files = list((kb_path / "cases").glob("*/case.md")) if (kb_path / "cases").is_dir() else []
    stale = not catalog_file.exists() or any(
        f.stat().st_mtime > catalog_file.stat().st_mtime for f in case_files)
    if stale and case_files:
        try:
            rebuild_catalog(kb_path)
        except OSError:                     # read-only install: index in memory
            return scan_cases(kb_path)
    return json.loads(catalog_file.read_text(encoding="utf-8"))


def filter_cases(
    catalog: dict,
    case_ids: list[str] | None = None,
    capabilities: list[str] | None = None,
    tender_tags: list[str] | None = None,
    sector: str | None = None,
    client_type: str | None = None,
    status: str | None = None,
    exclude_confidential: bool = False,
) -> list[dict]:
    cases = catalog["cases"]

    if case_ids:
        id_set = set(case_ids)
        cases = [c for c in cases if c["case_id"] in id_set or c["slug"] in id_set]

    if capabilities:
        caps = set(c.lower() for c in capabilities)
        cases = [c for c in cases if caps & {x.lower() for x in c.get("capabilities", [])}]

    if tender_tags:
        tags = set(t.lower() for t in tender_tags)
        cases = [c for c in cases if tags & {x.lower() for x in c.get("tender_tags", [])}]

    if sector:
        cases = [c for c in cases if sector.lower() in c.get("sector", "").lower()]

    if client_type:
        cases = [c for c in cases if client_type.lower() in c.get("client_type", "").lower()]

    if status:
        cases = [c for c in cases if status.lower() in c.get("status", "").lower()]

    if exclude_confidential:
        cases = [c for c in cases if c.get("confidentiality") != "confidential"]

    return cases


def read_case_content(kb_path: Path, file_path: str) -> str:
    return (kb_path / file_path).read_text(encoding="utf-8")


def parse_frontmatter(content: str) -> dict:
    """Return the YAML frontmatter of a case.md as a dict ({} if none/invalid)."""
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    try:
        import yaml
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


def split_case(content: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body) where body is everything after the
    frontmatter block (or the whole content if there is none)."""
    m = re.match(r"^---\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not m:
        return {}, content
    try:
        import yaml
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    return meta, m.group(2)


# ---------------------------------------------------------------------------
# Duplicate detection + merging (for the add_case flow)
# ---------------------------------------------------------------------------

def find_similar_cases(catalog: dict, *, client: str = "", title: str = "",
                       slug: str = "", capabilities: list[str] | None = None,
                       threshold: float = 0.55) -> list[dict]:
    """Score existing cases against an incoming one and return likely matches.

    Signals: client-name match (strongest), title similarity, slug similarity,
    and capability overlap. Returns ranked dicts above `threshold`.
    """
    import difflib

    def ratio(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() if a and b else 0.0

    caps = {c.lower() for c in (capabilities or [])}
    out = []
    for c in catalog.get("cases", []):
        score, reasons = 0.0, []

        cr = ratio(client, c.get("client", ""))
        if cr > 0.9:
            score += 0.55; reasons.append(f"same client “{c.get('client')}”")
        elif cr > 0.6:
            score += 0.3; reasons.append("similar client")

        tr = ratio(title, c.get("title", ""))
        score += 0.30 * tr
        if tr > 0.7:
            reasons.append("similar title")

        sr = ratio(slug, c.get("slug", ""))
        score += 0.15 * sr
        if sr > 0.8:
            reasons.append("similar slug")

        if caps:
            ccaps = {x.lower() for x in c.get("capabilities", [])}
            if ccaps:
                overlap = len(caps & ccaps) / max(1, len(caps | ccaps))
                score += 0.15 * overlap
                if overlap > 0.4:
                    reasons.append("overlapping capabilities")

        if score >= threshold:
            out.append({"slug": c["slug"], "title": c.get("title", ""),
                        "client": c.get("client", ""), "score": round(score, 2),
                        "reasons": reasons, "file_path": c.get("file_path", "")})
    return sorted(out, key=lambda x: -x["score"])


def _parse_sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    """Split a case body into (preamble, [(heading_line, section_body), ...]).

    preamble is everything before the first H2 (## ...)."""
    parts = re.split(r"(?m)^(## .+)$", body)
    preamble = parts[0]
    sections = []
    for i in range(1, len(parts) - 1, 2):
        sections.append((parts[i].strip(), parts[i + 1]))
    return preamble, sections


def merge_cases(existing_md: str, new_md: str) -> str:
    """Merge a new case into an existing one.

    Frontmatter: list fields are unioned; scalar fields prefer the new value
    when non-empty, else keep existing; last_updated is set to today.
    Body: section-by-section, the new content wins when non-empty, otherwise
    the existing content is kept; sections unique to either side are retained.
    """
    import yaml
    from datetime import date

    old_meta, old_body = split_case(existing_md)
    new_meta, new_body = split_case(new_md)

    merged_meta = dict(old_meta)
    for k, v in new_meta.items():
        if isinstance(v, list) or isinstance(old_meta.get(k), list):
            seen, union = set(), []
            for item in (ensure_list(old_meta.get(k)) + ensure_list(v)):
                key = str(item).lower()
                if key not in seen:
                    seen.add(key); union.append(item)
            merged_meta[k] = union
        elif v not in (None, "", []):
            merged_meta[k] = v
    merged_meta["last_updated"] = date.today().isoformat()

    old_pre, old_secs = _parse_sections(old_body)
    new_pre, new_secs = _parse_sections(new_body)
    new_by_head = {h.lower(): (h, b) for h, b in new_secs}

    merged_secs, used = [], set()
    for head, body in old_secs:
        key = head.lower()
        if key in new_by_head and new_by_head[key][1].strip():
            merged_secs.append((head, new_by_head[key][1]))
            used.add(key)
        else:
            merged_secs.append((head, body))
    for head, body in new_secs:           # sections only in the new doc
        if head.lower() not in used and head.lower() not in {h.lower() for h, _ in old_secs}:
            merged_secs.append((head, body))

    fm = yaml.safe_dump(merged_meta, allow_unicode=True, sort_keys=False,
                        default_flow_style=False).strip()
    preamble = (new_pre if new_pre.strip() else old_pre).rstrip()
    body = preamble + "\n\n" + "\n".join(f"{h}{b}" for h, b in merged_secs)
    return f"---\n{fm}\n---\n\n{body.strip()}\n"


def ensure_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def rebuild_catalog(kb_path: Path) -> int:
    """Rebuild catalog.json from cases/. Returns the number of cases indexed."""
    import json as _json

    catalog = scan_cases(kb_path)
    (kb_path / "catalog.json").write_text(
        _json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog["total_cases"]


def scan_cases(kb_path: Path) -> dict:
    """Index every cases/<slug>/case.md into a catalog dict."""
    from datetime import datetime, timezone

    cases_dir = kb_path / "cases"
    cases = []
    for case_dir in sorted(d for d in cases_dir.iterdir() if d.is_dir()):
        f = case_dir / "case.md"
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        if not meta:
            continue
        cases.append({
            "case_id": str(meta.get("case_id", "")),
            "slug": case_dir.name,
            "file_path": f"cases/{case_dir.name}/case.md",
            "title": str(meta.get("title", "")),
            "client": str(meta.get("client", "")),
            "sector": str(meta.get("sector", "")),
            "client_type": str(meta.get("client_type", "")),
            "period": str(meta.get("period", "")),
            "status": str(meta.get("status", "")),
            "confidentiality": str(meta.get("confidentiality", "")),
            "budget_order": str(meta.get("budget_order", "")),
            "effort_order": str(meta.get("effort_order", "")),
            "contact_person": str(meta.get("contact_person", "")),
            "last_updated": str(meta.get("last_updated", "")),
            "technologies": ensure_list(meta.get("technologies")),
            "capabilities": ensure_list(meta.get("capabilities")),
            "tender_tags": ensure_list(meta.get("tender_tags")),
            "reusable_for": ensure_list(meta.get("reusable_for")),
            "aliases": ensure_list(meta.get("aliases")),
            "sections": re.findall(r"^## (.+)$", text, re.MULTILINE),
            "summary": extract_section(text, 1),
        })
    catalog = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(cases),
        "cases": cases,
    }
    return catalog


def extract_section(content: str, number: int) -> str:
    # NB: [^\n]* (not .+) for the title — under re.DOTALL a bare .+ would
    # greedily swallow the whole document and leave the body capture empty.
    pattern = rf"^## {number}\. [^\n]*\n+(.*?)(?=^## |\Z)"
    m = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def get_client_display(case: dict) -> str:
    """Return displayable client name, anonymized if needed."""
    if case.get("confidentiality") == "confidential":
        return case.get("sector", "Confidential client")
    return case.get("client", "Unknown")


# Trailing words that are part of a legal/trading name but not how people
# refer to the client in prose ("BlueCrate Logistics" -> "BlueCrate").
_NAME_SUFFIXES = {
    "logistics", "retail", "group", "holding", "holdings", "company", "corp",
    "corporation", "inc", "ltd", "llc", "bv", "nv", "sa", "gmbh", "ag", "plc",
    "solutions", "services", "systems", "technologies", "international",
    "belgium", "nederland", "netherlands", "europe",
}


def _client_aliases(case: dict) -> list[str]:
    """Every way a confidential client's name may appear in its case text:
    the full name, any `aliases` from the frontmatter, and the name without
    generic suffixes. Longest first, so "BlueCrate Logistics" is replaced
    before "BlueCrate"."""
    client = (case.get("client") or "").strip()
    names = {client, *(str(a).strip() for a in ensure_list(case.get("aliases")))}
    words = client.split()
    while len(words) > 1 and words[-1].lower().strip(".,") in _NAME_SUFFIXES:
        words.pop()
    names.add(" ".join(words))
    return sorted((n for n in names if len(n) >= 3), key=len, reverse=True)


def redact_client(text: str, case: dict) -> str:
    """Replace a confidential client's name with "the client". No-op for
    public/anonymized cases."""
    if case.get("confidentiality") != "confidential" or not text:
        return text

    def sub(m: re.Match) -> str:
        line = text[:m.start()].rsplit("\n", 1)[-1].strip()   # same line, before the name
        before = text[:m.start()].rstrip()
        sentence_start = (not before or before[-1] in ".!?:"
                          or not line.strip("-*•#>0123456789.) "))
        return "The client" if sentence_start else "the client"

    for name in _client_aliases(case):
        text = re.sub(rf"(?<!\w){re.escape(name)}(?!\w)", sub, text)
    return text


def get_case_title(case: dict) -> str:
    """The case title, with a confidential client's name removed."""
    title = case.get("title", "")
    if case.get("confidentiality") != "confidential":
        return title
    for name in _client_aliases(case):
        title = re.sub(rf"(?<!\w){re.escape(name)}('s)?(?!\w)\s*", "", title)
    title = title.strip(" -—:")
    return (title[:1].upper() + title[1:]) if title else get_client_display(case)


def read_case(kb_path: Path, case: dict) -> str:
    """Case markdown, ready for slides: confidential client names redacted."""
    return redact_client(read_case_content(kb_path, case["file_path"]), case)


# Tags are stored lowercase; these stay uppercase when shown as labels.
_ACRONYMS = {
    "ai", "ml", "llm", "llms", "rag", "ocr", "api", "apis", "erp", "crm", "poc",
    "nlp", "bi", "etl", "kpi", "sla", "gdpr", "iot", "ui", "ux", "hr", "it",
    "sql", "pdf", "mvp", "saas", "cv", "gpu",
}


def display_label(tag: str) -> str:
    """Title-case a tag for display without mangling acronyms or names
    ("rag" -> "RAG", "human in the loop" -> "Human In The Loop",
    "LangChain" stays "LangChain")."""
    def word(w: str) -> str:
        if w.lower() in _ACRONYMS:
            return w.upper()
        if any(c.isupper() for c in w):
            return w
        return w[:1].upper() + w[1:]
    return " ".join(word(w) for w in tag.split())


_LIST_ITEM = re.compile(r"^([-•*]|\d+[.)])\s+")


def _unwrap(text: str) -> str:
    """Join hard-wrapped lines back into paragraphs.

    Case files are usually wrapped at ~80 columns; those line breaks are an
    editing artefact, not content, and would otherwise land mid-sentence on
    the slide. Blank lines, headings and list items still start a new line.
    """
    out: list[str] = []
    for line in text.split("\n"):
        s = line.strip()
        if (s and out and out[-1] and not _LIST_ITEM.match(s)
                and not s.startswith("#") and not out[-1].startswith("#")):
            out[-1] = f"{out[-1]} {s}"
        else:
            out.append(s)
    return "\n".join(out)


def strip_markdown(text: str) -> str:
    """Remove markdown formatting for plain-text slide content."""
    text = _unwrap(text)
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text.strip()


def extract_bullets(text: str, max_bullets: int = 5) -> list[str]:
    """Extract concise bullet points from a markdown section.

    Prefers real list items (lines starting with -, *, • or "1."). If the
    section is prose, splits it into sentence-length bullets instead of
    dumping a whole paragraph as a single bullet.
    """
    clean = strip_markdown(text)
    lines = [ln.strip() for ln in clean.split("\n") if ln.strip()]

    # 1. Real markdown list items take priority.
    list_items = []
    for line in lines:
        if _LIST_ITEM.match(line):
            item = _LIST_ITEM.sub("", line).strip()
            if len(item) > 3:
                list_items.append(item)
    if list_items:
        return list_items[:max_bullets]

    # 2. Otherwise sentence-split the prose into bullets.
    prose = " ".join(lines)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose) if len(s.strip()) > 20]
    if sentences:
        return sentences[:max_bullets]

    # 3. Fallback: any non-trivial line.
    return [ln for ln in lines if len(ln) > 10][:max_bullets]


def split_lead(text: str) -> str:
    """The prose around a markdown list ("We start by… - item - item"), or ""
    when the section is all list or all prose. extract_bullets keeps only the
    list items, so this is what would otherwise go missing from the slide."""
    lines = [ln.strip() for ln in strip_markdown(text).split("\n")]
    if not any(_LIST_ITEM.match(ln) for ln in lines):
        return ""
    prose = [ln for ln in lines if ln and not _LIST_ITEM.match(ln)]
    return "\n".join(prose)


def truncate(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_period = cut.rfind(". ")
    return (cut[:last_period + 1] if last_period > max_chars // 2 else cut) + "…"
