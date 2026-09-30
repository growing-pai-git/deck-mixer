"""Deck Mixer — local Python MCP server.

Minimal Claude Desktop setup (no env vars needed after first run):

    {
      "mcpServers": {
        "deck-mixer": {
          "command": "pandoro",
          "args": ["deck-mixer", "mcp", "serve"],
          "cwd": "/absolute/path/to/your-case-library"
        }
      }
    }

Then ask Claude to run `configure_keys` to set API keys and preferences.
Keys are saved to ~/.config/pandoro/keys.json (owner-only permissions).

Optional env var overrides (take priority over saved config):
  LIBRARY_PATH      Path to a case library (see CASE_LIBRARY_SCHEMA.md).
  THEME_PATH        Path to a theme.yaml/theme.json (see theme.py).
  BRAND_DESCRIPTION Free-text brand description (used when no THEME_PATH is set).
  OUTPUT_DIR        Where to save generated .pptx files.
  TEMPLATE_PATH     Optional branded .pptx/.potx template.
  ANTHROPIC_API_KEY Claude enrichment key.
  PEXELS_API_KEY    Pexels stock photo key.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # mcp>=2.0 renamed/moved FastMCP -> mcp.server.mcpserver.MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP

from .builder import (
    build_capabilities_deck,
    build_plan_deck,
    build_reference_deck,
    build_tender_deck,
)
from .config import (
    inject_keys, is_first_run, load_config, mark_setup_done, mask, save_config,
)
from .kb import (
    filter_cases, find_similar_cases, load_catalog, merge_cases,
    parse_frontmatter, rebuild_catalog,
)
from .theme import load_theme

# Inject saved keys into os.environ before resolving any config below
inject_keys()

# --- Configuration ---------------------------------------------------------

_SAMPLE_LIBRARY = (Path(__file__).parent / "examples" / "sample-library").resolve()


def _resolve_library_path() -> Path:
    env = os.environ.get("LIBRARY_PATH")
    if env:
        return Path(env).expanduser().resolve()
    from .config import get
    cfg = get("library_path")
    if cfg:
        return Path(cfg).expanduser().resolve()
    if _SAMPLE_LIBRARY.exists():
        return _SAMPLE_LIBRARY
    return Path(__file__).parent.parent.resolve()


def _resolve_output_dir() -> Path:
    env = os.environ.get("OUTPUT_DIR")
    if env:
        p = Path(env).expanduser().resolve()
    else:
        p = Path.home() / "Desktop" / "decks"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _resolve_template() -> str | None:
    env = os.environ.get("TEMPLATE_PATH")
    if env:
        p = Path(env).expanduser().resolve()
        return str(p) if p.exists() else None
    return None


def _resolve_theme():
    from .config import get
    return load_theme(theme_path=get("theme_path"), brand_description=get("brand_description"))


KB_PATH = _resolve_library_path()
OUTPUT_DIR = _resolve_output_dir()
TEMPLATE_PATH = _resolve_template()
THEME = _resolve_theme()

# --- MCP server -------------------------------------------------------------

mcp = FastMCP(
    "deck-mixer",
    instructions=(
        "Deck Mixer turns a case-study library into branded PPTX decks. "
        "On first use, the deck tools return a setup prompt: ask the user for "
        "their API keys and call configure_keys (or call it with no keys to "
        "proceed without). After that, use list_cases to explore the library, "
        "then create_reference_deck, create_capabilities_deck, create_tender_deck, "
        "or create_plan_deck to generate PPTX files. "
        "To add a case to the library, use add_case — it checks for an "
        "existing match first and asks whether to replace, add, or merge; never "
        "skip that confirmation. Use remove_case to archive (or hard-delete) a "
        "case. "
        f"Library at: {KB_PATH}. Output dir: {OUTPUT_DIR}."
    ),
)


def _catalog():
    return load_catalog(KB_PATH)


# Names that arrive as tool arguments become path components, so they must be
# a single plain segment: no separators, no leading dot ("..", ".hidden").
_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_FILENAME_RE = re.compile(r"\w[\w .-]*")


def _filename_error(filename: str | None) -> str | None:
    if filename and not _FILENAME_RE.fullmatch(filename):
        return (f"Invalid filename {filename!r}: use a plain name (letters, "
                "digits, spaces, '-', '_', '.'), no folders.")
    return None


def _outfile(prefix: str, filename: str | None = None) -> Path:
    if filename:
        if _filename_error(filename):
            raise ValueError(f"Invalid filename {filename!r}")
        return OUTPUT_DIR / f"{filename}.pptx"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"{prefix}-{ts}.pptx"


def _library_edit_error(*slugs: str | None) -> str | None:
    """Why add_case/remove_case must refuse, or None if the edit is safe."""
    if KB_PATH == _SAMPLE_LIBRARY:
        return ("No case library is configured — refusing to edit the bundled "
                "sample library. Set LIBRARY_PATH (or library_path via "
                "configure_keys) to your own library first.")
    for slug in slugs:
        if slug is not None and not _SLUG_RE.fullmatch(slug):
            return (f"Invalid slug {slug!r}: use letters, digits, '-', '_' or '.', "
                    "with no folders.")
    return None


_ONBOARDING = """\
👋 Welcome to Pandoro — first-time setup.

WHAT THIS DOES: builds branded PowerPoint decks straight from the case
library (cases/*/case.md). An AI "art director" plans each slide's layout
from what that slide actually needs to say (not a fixed template), and
generates on-brand imagery to match. Four deck types:

  • create_reference_deck    deep dive on one or more specific cases
  • create_capabilities_deck portfolio overview, grouped by capability/tag
  • create_tender_deck       evidence deck for a tender/pitch, with a brief
  • create_plan_deck         free-form deck from your own title + markdown

Typical flow: list_cases (find the 2-5 relevant ones) -> create_*_deck.

SETUP — everything below is OPTIONAL. Decks still build with zero keys
(layout heuristics + free stock photos), but each key you add unlocks more.
This is a multi-provider tool by design — plug in whichever API you already
have a key for, no need to collect every one:

  Planning ("art director" — per-slide layout choice, visual judgment).
  Uses whichever of these is set (llm_provider picks which, "auto" = first
  configured):
      • GEMINI_API_KEY      aistudio.google.com — free tier, and ALSO
                            powers image generation below (get this ONE
                            key first for the fastest start)
      • ANTHROPIC_API_KEY   console.anthropic.com
      • OPENAI_API_KEY      platform.openai.com — also powers image gen

  AI image generation — pick ONE provider (image_provider, "auto" = first
  configured):
      • GEMINI_API_KEY       Google Gemini 2.5 Flash image (free tier)
      • OPENAI_API_KEY       OpenAI gpt-image-1
      • STABILITY_API_KEY / TOGETHER_API_KEY / FAL_KEY / REPLICATE_API_TOKEN

  Stock photos (authentic subjects / fallback — no AI key needed):
      • PEXELS_API_KEY       pexels.com/api, free
      • UNSPLASH_ACCESS_KEY  unsplash.com/developers

FASTEST START: one free Gemini key covers BOTH planning and images —
get one at aistudio.google.com.

ACTION: Ask the user which keys they have (or suggest the fastest-start tip
above), then call `configure_keys` with whatever they give you — only set
llm_provider/image_provider if they want to override "auto". To proceed with
zero keys, call `configure_keys` with none — that records setup so you won't
be asked again. Tip: run `preview_image` to confirm imagery actually comes
back, and `show_config` any time to check what's active.
"""


def _first_run_guard() -> str | None:
    """Return the onboarding prompt the first time a deck tool is used."""
    return _ONBOARDING if is_first_run() else None


# ---------------------------------------------------------------------------
# Tool: list_cases
# ---------------------------------------------------------------------------

@mcp.tool()
def list_cases(
    capabilities: list[str] | None = None,
    tender_tags: list[str] | None = None,
    sector: str | None = None,
    client_type: str | None = None,
    status: str | None = None,
    exclude_confidential: bool = False,
) -> str:
    """
    Query the case catalog.

    Returns a JSON list of matching cases with their metadata.
    Use the returned slug or case_id values in the deck-creation tools.

    Args:
        capabilities: Filter to cases with ANY of these capability values
                      (e.g. ["RAG", "AI agent"])
        tender_tags:  Filter to cases with ANY of these tender tag values
                      (e.g. ["governance", "human in the loop"])
        sector:       Substring match on sector (e.g. "energie")
        client_type:  Substring match on client_type (e.g. "enterprise", "kmo")
        status:       Substring match on status (e.g. "production", "poc")
        exclude_confidential: If true, exclude cases with confidentiality=confidential
    """
    catalog = _catalog()
    cases = filter_cases(
        catalog,
        capabilities=capabilities,
        tender_tags=tender_tags,
        sector=sector,
        client_type=client_type,
        status=status,
        exclude_confidential=exclude_confidential,
    )
    result = [
        {
            "slug": c["slug"],
            "case_id": c["case_id"],
            "title": c["title"],
            "client": c["client"],
            "sector": c["sector"],
            "status": c["status"],
            "confidentiality": c["confidentiality"],
            "capabilities": c.get("capabilities", []),
            "tender_tags": c.get("tender_tags", []),
            "technologies": c.get("technologies", []),
            "summary": c.get("summary", "")[:300],
        }
        for c in cases
    ]
    return json.dumps(result, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Tool: add_case
# ---------------------------------------------------------------------------

@mcp.tool()
def add_case(
    slug: str,
    content_md: str,
    resolution: str | None = None,
    target_slug: str | None = None,
) -> str:
    """
    Add a case to the knowledge base, checking first for an existing match.

    The content_md must be a full case.md (YAML frontmatter + body). On the
    first call the tool looks for an existing case that appears to be the same
    (by client, title, slug, capabilities). If a likely match is found and no
    `resolution` is given, it returns the match(es) and asks how to proceed —
    DO NOT guess; ask the user to choose:

      • replace — overwrite the existing case with the new content
      • add     — keep both; save as a new, separate case
      • merge   — combine: new section content wins, existing is kept where the
                  new doc is silent; list fields (tech/capabilities/tags) unioned

    Then call add_case again with `resolution` set (and `target_slug` = the
    existing case's slug for replace/merge). If no match is found, the case is
    added straight away. The catalog is rebuilt automatically.

    Args:
        slug:        Folder slug for a NEW case (used for "add"). e.g. "acme-rag".
        content_md:  Full case.md content (frontmatter + body).
        resolution:  None (detect) | "replace" | "add" | "merge".
        target_slug: The existing case to replace/merge into (from the match list).

    Returns:
        A conflict prompt (detect phase) or a confirmation of what was written.
    """
    if (err := _library_edit_error(slug, target_slug)):
        return err
    meta = parse_frontmatter(content_md)
    if not meta:
        return ("The content_md has no YAML frontmatter (--- ... ---). "
                "Add at least: case_id, title, client, status, confidentiality.")

    client = str(meta.get("client", ""))
    title = str(meta.get("title", ""))
    caps = meta.get("capabilities") or []
    catalog = _catalog()

    # --- Detect phase --------------------------------------------------------
    if resolution is None:
        matches = find_similar_cases(catalog, client=client, title=title,
                                     slug=slug, capabilities=caps)
        if matches:
            lines = [
                f"  • {m['slug']}  (match {int(m['score'] * 100)}%) — "
                f"{m['title'] or m['client']}  [{', '.join(m['reasons'])}]"
                for m in matches[:5]
            ]
            return (
                f"⚠️ A similar case already exists for “{client or title}”. "
                f"Ask the user how to proceed before writing.\n\n"
                f"Possible match(es):\n" + "\n".join(lines) + "\n\n"
                f"Re-call add_case with:\n"
                f"  resolution=\"replace\", target_slug=\"{matches[0]['slug']}\"  "
                f"(overwrite it)\n"
                f"  resolution=\"merge\",   target_slug=\"{matches[0]['slug']}\"  "
                f"(combine them)\n"
                f"  resolution=\"add\"                                   "
                f"(keep both as a new case)"
            )
        resolution = "add"  # nothing similar — proceed as a new case

    # --- Apply phase ---------------------------------------------------------
    cases_dir = KB_PATH / "cases"

    if resolution == "add":
        dest = cases_dir / slug
        if dest.exists():
            return (f"A case folder “{slug}” already exists. Choose a different "
                    f"slug, or use resolution=\"replace\"/\"merge\" with "
                    f"target_slug=\"{slug}\".")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "case.md").write_text(content_md, encoding="utf-8")
        action = f"Added new case “{slug}”"

    elif resolution in ("replace", "merge"):
        tslug = target_slug or slug
        target_file = cases_dir / tslug / "case.md"
        if not target_file.exists():
            return f"Target case “{tslug}” not found. Pass a valid target_slug."
        if resolution == "replace":
            target_file.write_text(content_md, encoding="utf-8")
            action = f"Replaced case “{tslug}” with the new content"
        else:
            merged = merge_cases(target_file.read_text(encoding="utf-8"), content_md)
            target_file.write_text(merged, encoding="utf-8")
            action = f"Merged the new content into existing case “{tslug}”"
    else:
        return ("resolution must be one of: replace, add, merge "
                "(or omit it to check for duplicates first).")

    count = rebuild_catalog(KB_PATH)
    return f"{action}. Catalog rebuilt — {count} cases indexed."


# ---------------------------------------------------------------------------
# Tool: create_reference_deck
# ---------------------------------------------------------------------------

@mcp.tool()
def create_reference_deck(
    case_ids: list[str],
    filename: str | None = None,
) -> str:
    """
    Generate a reference case PPTX deck for one or more cases.

    Produces one slide group per case following the standard section-to-slide mapping:
    Cover → Summary → Context & Challenge → Approach → Solution → Tech Stack → Results.
    Tender Relevance (section 12) is placed in speaker notes.

    Args:
        case_ids: List of slug or case_id values (from list_cases).
                  Example: ["northwind-retail-support", "port-authority-document-intake"]
        filename: Optional output filename (without extension).
                  Default: auto-generated with timestamp.

    Returns:
        Path to the generated .pptx file.
    """
    if (msg := _first_run_guard()):
        return msg
    if (err := _filename_error(filename)):
        return err
    catalog = _catalog()
    cases = filter_cases(catalog, case_ids=case_ids)
    if not cases:
        return f"No cases found for: {case_ids}"

    out = _outfile("reference", filename)
    path = build_reference_deck(cases, KB_PATH, out, TEMPLATE_PATH, theme=THEME)
    return f"Created reference deck ({len(cases)} case(s)): {path}"


# ---------------------------------------------------------------------------
# Tool: create_capabilities_deck
# ---------------------------------------------------------------------------

@mcp.tool()
def create_capabilities_deck(
    capabilities: list[str] | None = None,
    tender_tags: list[str] | None = None,
    exclude_confidential: bool = False,
    group_by: str = "capabilities",
    filename: str | None = None,
) -> str:
    """
    Generate a capabilities overview PPTX deck.

    Groups cases by capability or tender tag. Useful for showing the full
    portfolio breadth or a filtered slice (e.g. only production AI cases).

    Args:
        capabilities:         Filter to cases with ANY of these capabilities.
        tender_tags:          Filter to cases with ANY of these tender tags.
        exclude_confidential: Exclude confidential cases (safer for public decks).
        group_by:             "capabilities" or "tender_tags". Default: "capabilities".
        filename:             Optional output filename (without extension).

    Returns:
        Path to the generated .pptx file.
    """
    if (msg := _first_run_guard()):
        return msg
    if (err := _filename_error(filename)):
        return err
    if group_by not in ("capabilities", "tender_tags"):
        return "group_by must be 'capabilities' or 'tender_tags'"

    catalog = _catalog()
    cases = filter_cases(
        catalog,
        capabilities=capabilities,
        tender_tags=tender_tags,
        exclude_confidential=exclude_confidential,
    )
    if not cases:
        return "No cases match the given filters."

    out = _outfile("capabilities", filename)
    path = build_capabilities_deck(cases, KB_PATH, out, group_by=group_by,
                                   template_path=TEMPLATE_PATH, theme=THEME)
    return f"Created capabilities deck ({len(cases)} cases, grouped by {group_by}): {path}"


# ---------------------------------------------------------------------------
# Tool: create_tender_deck
# ---------------------------------------------------------------------------

@mcp.tool()
def create_tender_deck(
    tender_tags: list[str] | None = None,
    capabilities: list[str] | None = None,
    case_ids: list[str] | None = None,
    brief: str = "",
    exclude_confidential: bool = False,
    filename: str | None = None,
) -> str:
    """
    Generate a tender-ready PPTX deck with evidence slides per case.

    Each case slide shows: client, summary, results/impact, tech chips.
    Speaker notes contain the tender relevance framing (section 12).

    Args:
        tender_tags:          Filter cases by ANY of these tender tags.
        capabilities:         Filter cases by ANY of these capabilities.
        case_ids:             Explicitly include specific cases by slug or case_id.
        brief:                Short tender context paragraph (appears on slide 2).
        exclude_confidential: Exclude confidential cases. Default: False.
        filename:             Optional output filename (without extension).

    Returns:
        Path to the generated .pptx file.
    """
    if (msg := _first_run_guard()):
        return msg
    if (err := _filename_error(filename)):
        return err
    catalog = _catalog()
    cases = filter_cases(
        catalog,
        case_ids=case_ids,
        capabilities=capabilities,
        tender_tags=tender_tags,
        exclude_confidential=exclude_confidential,
    )
    if not cases:
        return "No cases match the given filters."

    out = _outfile("tender", filename)
    path = build_tender_deck(cases, KB_PATH, out, brief=brief,
                             template_path=TEMPLATE_PATH, theme=THEME)
    return f"Created tender deck ({len(cases)} cases): {path}"


# ---------------------------------------------------------------------------
# Tool: create_plan_deck
# ---------------------------------------------------------------------------

@mcp.tool()
def create_plan_deck(
    title: str,
    content_md: str,
    subtitle: str = "",
    label: str = "Plan of Approach",
    company: str = "",
    enrich: bool = True,
    filename: str | None = None,
) -> str:
    """
    Generate a PPTX deck from any markdown document — plans, proposals, briefings.

    Each H2 heading (## ...) becomes one slide. Headings that start with
    "Fase", "Phase", "Stap", or "Etappe" get a full-bleed section-divider
    slide (in the theme's primary colour) followed by a content slide.

    Planning (when GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY is set):
      A 'planner' step reads the storyline and assigns each slide a layout and
      visual treatment — statement, clean bullets, photo-split, quote, or
      diagram — so the deck has a varied rhythm instead of identical slides.
      Without a key it falls back to sensible layout heuristics.

    Imagery (when an image-provider or stock-photo key is set):
      Each content slide gets a relevant on-brand image (AI-generated or
      stock photo, see configure_keys for the full provider list).

    Both enhancements are progressive — the deck still generates without any
    API keys. If none are configured, the result now leads with an explicit
    warning instead of silently degrading.

    Args:
        title:      Cover slide main title. Use \\n for line breaks.
        content_md: Full markdown content. H2 headings drive the slide structure.
        subtitle:   Cover subtitle (client name, date, etc.).
        label:      Small label above the title (e.g. "Plan of Approach").
        company:    Client/company name — gives Claude context for tone.
        enrich:     Set to false to skip Claude enrichment even if key is present.
        filename:   Optional output filename without extension.

    Returns:
        Path to the generated .pptx file.
    """
    if (msg := _first_run_guard()):
        return msg
    if (err := _filename_error(filename)):
        return err

    warning = _missing_key_warning()
    out = _outfile("plan", filename)
    path = build_plan_deck(
        title=title,
        content_md=content_md,
        subtitle=subtitle,
        label=label,
        company=company,
        enrich=enrich,
        output_path=out,
        template_path=TEMPLATE_PATH,
        theme=THEME,
    )
    return f"{warning}Created plan deck: {path}"


def _missing_key_warning() -> str:
    """Warn upfront (before reporting the built deck) about any enhancement
    that has no configured key, instead of silently degrading. Checks every
    supported planning/image provider, not just Anthropic/Pexels."""
    from . import llm
    from .imagegen import configured_providers as image_providers

    missing = []
    if not llm.configured_providers():
        missing.append("AI planning (falling back to layout heuristics) — "
                       "set GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY")
    if not image_providers() and not os.environ.get("PEXELS_API_KEY") \
            and not os.environ.get("UNSPLASH_ACCESS_KEY"):
        missing.append("Images (slides get placeholders to replace with your own pictures) — "
                       "set GEMINI_API_KEY, PEXELS_API_KEY, or another image key")
    if not missing:
        return ""
    lines = "\n".join(f"  ✗ {m}" for m in missing)
    return (f"⚠️  Missing API keys — building with reduced quality:\n{lines}\n"
            f"Run configure_keys to add one (a free GEMINI_API_KEY covers both).\n\n")


# ---------------------------------------------------------------------------
# Tool: configure_keys
# ---------------------------------------------------------------------------

@mcp.tool()
def configure_keys(
    anthropic_api_key: str | None = None,
    openai_api_key: str | None = None,
    gemini_api_key: str | None = None,
    llm_provider: str | None = None,
    stability_api_key: str | None = None,
    together_api_key: str | None = None,
    fal_key: str | None = None,
    replicate_api_token: str | None = None,
    image_provider: str | None = None,
    image_theme: str | None = None,
    image_art_style: str | None = None,
    image_prefer_generate: str | None = None,
    pexels_api_key: str | None = None,
    unsplash_access_key: str | None = None,
    output_dir: str | None = None,
    template_path: str | None = None,
    library_path: str | None = None,
    theme_path: str | None = None,
    brand_description: str | None = None,
) -> str:
    """
    Save API keys and preferences for pandoro.

    Values are stored in ~/.config/pandoro/keys.json with owner-only
    file permissions. Environment variables always take priority over saved
    values, so per-session overrides still work.

    Call with no arguments to see the current configuration status.

    Args:
        — Planning "art director" (layout choice, visual judgment, deck mood).
          Configure any one or more of these, then pick with llm_provider —
        anthropic_api_key:   Anthropic Claude (console.anthropic.com).
        gemini_api_key:      Google Gemini (aistudio.google.com) — shared with
                             image generation below.
        openai_api_key:      OpenAI — shared with image generation below.
        llm_provider:        Which planning LLM to use: "auto" (default — first
                             configured, in order gemini/claude/openai) or one
                             of: gemini, claude, openai. Different people can
                             plug in whichever provider they have a key for.

        — AI image generation (configure one or more, then pick with image_provider) —
        stability_api_key:   Stability AI stable-image core.
        together_api_key:    Together AI FLUX.1-schnell (api.together.xyz).
        fal_key:             fal.ai FLUX schnell.
        replicate_api_token: Replicate FLUX schnell.
        image_provider:      Which generator to use: "auto" (default — first
                             configured) or one of: openai, gemini, stability,
                             together, fal, replicate.
        image_theme:         Subject theme woven into every generation prompt,
                             e.g. "artisan bakery". Empty string clears it.
        image_art_style:     Rendering style for generated images, e.g.
                             "Studio Ghibli anime style". Empty string clears it.
        image_prefer_generate: "true" to make AI generation win even on slots
                             the planner marked as "photo". "false"/"" disables.

        — Stock photos (fallback / authentic subjects) —
        pexels_api_key:      Pexels — first stock-photo source (pexels.com/api).
        unsplash_access_key: Unsplash — backup (unsplash.com/developers).
        output_dir:        Folder where generated .pptx files are saved.
                           Default: ~/Desktop/decks
        template_path:     Absolute path to a branded .pptx/.potx template file.
                           Leave unset to use the theme's built-in style.

        — Case library and brand (restart the server to pick up changes) —
        library_path:       Path to a case-library folder (see
                            CASE_LIBRARY_SCHEMA.md). Falls back to the bundled
                            sample library, then the current directory.
        theme_path:          Path to a theme.yaml/theme.json (see theme.py).
                            Takes priority over brand_description.
        brand_description:   Free-text brand description used to infer a
                            palette/mood when no theme_path is set (requires
                            an LLM key). Falls back to a neutral default theme.

    Returns:
        Confirmation of what was saved and current feature status.
    """
    updates = {
        k: v for k, v in {
            "anthropic_api_key": anthropic_api_key,
            "openai_api_key": openai_api_key,
            "gemini_api_key": gemini_api_key,
            "llm_provider": llm_provider,
            "stability_api_key": stability_api_key,
            "together_api_key": together_api_key,
            "fal_key": fal_key,
            "replicate_api_token": replicate_api_token,
            "image_provider": image_provider,
            "image_theme": image_theme,
            "image_art_style": image_art_style,
            "image_prefer_generate": image_prefer_generate,
            "pexels_api_key": pexels_api_key,
            "unsplash_access_key": unsplash_access_key,
            "output_dir": output_dir,
            "template_path": template_path,
            "library_path": library_path,
            "theme_path": theme_path,
            "brand_description": brand_description,
        }.items() if v is not None
    }

    if updates:
        save_config(updates)
        # Inject newly saved keys into this process's env so they take effect immediately
        inject_keys()
        saved_keys = ", ".join(updates.keys())
        saved_msg = f"Saved: {saved_keys}\n\n"
    else:
        # No keys given — still record that setup happened so onboarding stops.
        mark_setup_done()
        saved_msg = ""

    cfg = load_config()

    from . import llm
    from .imagegen import configured_providers, active_provider, _PROVIDERS

    pexels    = os.environ.get("PEXELS_API_KEY")      or cfg.get("pexels_api_key")
    unsplash  = os.environ.get("UNSPLASH_ACCESS_KEY") or cfg.get("unsplash_access_key")
    provider  = os.environ.get("IMAGE_PROVIDER")      or cfg.get("image_provider", "auto")
    theme     = os.environ.get("IMAGE_THEME")         or cfg.get("image_theme", "")
    art_style = os.environ.get("IMAGE_ART_STYLE")     or cfg.get("image_art_style", "")
    prefer_gen = os.environ.get("IMAGE_PREFER_GENERATE") or cfg.get("image_prefer_generate", "")
    out_dir   = os.environ.get("OUTPUT_DIR")          or cfg.get("output_dir", str(Path.home() / "Desktop" / "decks"))
    tmpl      = os.environ.get("TEMPLATE_PATH")       or cfg.get("template_path")
    llm_provider = os.environ.get("LLM_PROVIDER")     or cfg.get("llm_provider", "auto")
    lib_path  = os.environ.get("LIBRARY_PATH")        or cfg.get("library_path")
    thm_path  = os.environ.get("THEME_PATH")          or cfg.get("theme_path")
    brand_desc = os.environ.get("BRAND_DESCRIPTION")  or cfg.get("brand_description", "")

    features = []
    llms = llm.configured_providers()
    if llms:
        labels = ", ".join(llm._PROVIDERS[n].label for n in llms)
        features.append(f"✓ Glaze planning + visual judgment: {labels}")
        features.append(f"  → active planner: {llm.active_provider()} (llm_provider={llm_provider})")
    else:
        features.append("✗ Glaze planning — add any one of anthropic_api_key/"
                        "gemini_api_key/openai_api_key to enable (falls back "
                        "to layout heuristics without one)")

    gens = configured_providers()
    if gens:
        labels = ", ".join(_PROVIDERS[n].label for n in gens)
        features.append(f"✓ AI image generation: {labels}")
        features.append(f"  → active generator: {active_provider()} (image_provider={provider})")
    else:
        features.append("✗ AI image generation — add a provider key "
                        "(openai/gemini/stability/together/fal/replicate)")

    photo_sources = ["Pexels"] if pexels else []
    if unsplash:
        photo_sources.append("Unsplash")
    if photo_sources:
        features.append("✓ Stock photos (fallback / authentic subjects): "
                        + " → ".join(photo_sources))
    else:
        features.append("✗ Stock photos — add PEXELS_API_KEY or UNSPLASH_ACCESS_KEY")
    if not gens and not photo_sources:
        features.append("  → no image source: slides get image placeholders to fill yourself")

    # Per-generator key lines (env key == config key uppercased); dedupe keys
    # shared across providers (e.g. GEMINI_API_KEY used by planning + images).
    seen_env: set[str] = set()
    key_lines_list = []
    for p in list(llm._PROVIDERS.values()) + list(_PROVIDERS.values()):
        if p.env_key in seen_env:
            continue
        seen_env.add(p.env_key)
        key_lines_list.append(
            f"  {p.env_key.ljust(19)} : "
            f"{mask(os.environ.get(p.env_key) or cfg.get(p.env_key.lower()))}")
    key_lines = "\n".join(key_lines_list)

    return (
        f"{saved_msg}"
        f"Current configuration\n"
        f"  LLM_PROVIDER        : {llm_provider}\n"
        f"  IMAGE_PROVIDER      : {provider}\n"
        f"  IMAGE_THEME         : {theme or '(none)'}\n"
        f"  IMAGE_ART_STYLE     : {art_style or '(none)'}\n"
        f"  IMAGE_PREFER_GENERATE: {prefer_gen or '(off)'}\n"
        f"{key_lines}\n"
        f"  PEXELS_API_KEY      : {mask(pexels)}\n"
        f"  UNSPLASH_ACCESS_KEY : {mask(unsplash)}\n"
        f"  Output folder       : {out_dir}\n"
        f"  Template            : {tmpl or '(built-in style)'}\n"
        f"  Library             : {lib_path or f'(active: {KB_PATH})'}\n"
        f"  Theme               : {thm_path or '(none — using brand_description/default)'}\n"
        f"  Brand description   : {brand_desc or '(none)'}\n\n"
        f"Features:\n" + "\n".join(f"  {f}" for f in features)
    )


# ---------------------------------------------------------------------------
# Tool: show_config
# ---------------------------------------------------------------------------

@mcp.tool()
def show_config() -> str:
    """
    Show the current deck mixer configuration and feature status.

    Displays which API keys are set, where decks are saved, and which
    optional features (content enrichment, photos) are active.
    Keys are masked — only the first and last characters are shown.
    """
    return configure_keys()


# ---------------------------------------------------------------------------
# Tool: preview_image
# ---------------------------------------------------------------------------

@mcp.tool()
def preview_image(hint: str = "artificial intelligence consulting",
                  medium: str = "generate") -> str:
    """
    Diagnostic: produce ONE image with the current settings and save it.

    Use this to confirm the beautify pipeline actually returns imagery before
    generating a full deck. It runs the same resolver the decks use — AI
    generation via the selected provider, falling back to stock photos —
    applies the brand style, and writes the result to the output folder.

    Args:
        hint:   Subject to depict (e.g. "data automation", "team collaboration").
        medium: "generate" (AI image, default) or "photo" (stock photo first).

    Returns:
        The saved image path plus which source produced it — or a clear message
        if no source returned an image (e.g. no provider key set).
    """
    from .visuals import resolve_image, visuals_status
    from .glaze.placeholders import BACKGROUND

    img = resolve_image(hint, role=BACKGROUND, medium=medium)
    if not img:
        from .imagegen import diagnose
        return ("No image was produced.\n\n"
                "Generator diagnostics:\n" + diagnose(hint) + "\n\n"
                + visuals_status() +
                "\n\nTip: a free Gemini key works with image_provider=gemini_flash. "
                "Imagen (image_provider=gemini) needs billing enabled.")

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUTPUT_DIR / f"preview-{ts}.png"
    path.write_bytes(img)
    return (f"Saved preview image ({len(img):,} bytes): {path}\n\n"
            + visuals_status())


# ---------------------------------------------------------------------------
# Tool: remove_case
# ---------------------------------------------------------------------------

@mcp.tool()
def remove_case(
    slug: str,
    hard_delete: bool = False,
) -> str:
    """
    Remove a case from the case library.

    By default the case folder is MOVED to _archive/{slug}/ so it can be
    recovered. Use hard_delete=true to permanently delete it.

    After archiving, catalog.json is automatically rebuilt.
    You still need to commit and push the changes to update the remote KB.

    Args:
        slug:        Case slug or case_id (from list_cases).
                     Example: "northwind-retail-support"
        hard_delete: If true, permanently deletes the case folder.
                     Default: false (archive to _archive/).

    Returns:
        Confirmation message with next steps.
    """
    import shutil
    import time

    if (err := _library_edit_error(slug)):
        return err
    cases_dir   = KB_PATH / "cases"
    archive_dir = KB_PATH / "_archive"

    # Resolve slug → directory
    case_dir = cases_dir / slug
    if not case_dir.is_dir():
        # Try matching by case_id in the catalog
        match = next((c for c in _catalog().get("cases", [])
                      if c.get("case_id") == slug), None)
        if match:
            slug = match["slug"]
            case_dir = cases_dir / slug
        if not case_dir.is_dir():
            available = ", ".join(d.name for d in sorted(cases_dir.iterdir()) if d.is_dir())
            return f"Case not found: '{slug}'\nAvailable: {available}"

    if hard_delete:
        shutil.rmtree(case_dir)
        action_msg = f"Permanently deleted: cases/{slug}/"
    else:
        archive_dir.mkdir(exist_ok=True)
        dest = archive_dir / slug
        if dest.exists():
            dest = archive_dir / f"{slug}-{int(time.time())}"
        shutil.move(str(case_dir), str(dest))
        action_msg = f"Archived: cases/{slug}/ → {dest.relative_to(KB_PATH)}/"

    count = rebuild_catalog(KB_PATH)
    return (
        f"✓ {action_msg}\n"
        f"✓ catalog.json rebuilt — {count} cases indexed\n\n"
        f"Next step — commit and push:\n"
        f"  git add -A && git commit -m 'remove: {slug}' && git push"
    )
