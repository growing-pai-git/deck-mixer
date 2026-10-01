"""Deck Mixer CLI — build decks from a case library, manage libraries/themes,
run the MCP server, or save API keys. Works standalone, no AI agent needed.

Registered under the `pandoro` umbrella CLI as the `deck-mixer` subcommand
(see pandoro/cli.py).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _library_path(args: argparse.Namespace) -> Path:
    if getattr(args, "library", None):
        return Path(args.library).expanduser().resolve()
    from .config import get
    cfg = get("library_path")
    if cfg:
        return Path(cfg).expanduser().resolve()
    sample = Path(__file__).parent / "examples" / "sample-library"
    if sample.exists():
        return sample.resolve()
    return Path.cwd()


def _theme(args: argparse.Namespace):
    from .theme import load_theme
    return load_theme(theme_path=getattr(args, "theme", None),
                      brand_description=getattr(args, "brand_description", None))


def _output_path(args: argparse.Namespace, prefix: str) -> Path:
    out_dir = Path(args.output_dir).expanduser().resolve() if getattr(args, "output_dir", None) \
        else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    if getattr(args, "filename", None):
        return out_dir / f"{args.filename}.pptx"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return out_dir / f"{prefix}-{ts}.pptx"


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def _key_notice(*, text: bool, images: bool) -> None:
    """Say what missing API keys cost this deck (stderr, so stdout stays the path)."""
    from .keys import HOW_CLI, missing_keys_notice
    notice = missing_keys_notice(text=text, images=images, how=HOW_CLI)
    if notice:
        print(notice.rstrip(), file=sys.stderr)


def cmd_build_reference(args: argparse.Namespace) -> None:
    from .builder import build_reference_deck
    from .kb import filter_cases, load_catalog

    lib = _library_path(args)
    cases = filter_cases(load_catalog(lib), case_ids=args.cases)
    if not cases:
        print(f"No cases found for: {args.cases}", file=sys.stderr)
        sys.exit(1)
    out = _output_path(args, "reference")
    path = build_reference_deck(cases, lib, out, args.template, theme=_theme(args))
    _key_notice(text=False, images=True)
    print(f"Created reference deck ({len(cases)} case(s)): {path}")


def cmd_build_capabilities(args: argparse.Namespace) -> None:
    from .builder import build_capabilities_deck
    from .kb import filter_cases, load_catalog

    lib = _library_path(args)
    cases = filter_cases(
        load_catalog(lib),
        capabilities=args.capabilities,
        tender_tags=args.tender_tags,
        exclude_confidential=args.exclude_confidential,
    )
    if not cases:
        print("No cases match the given filters.", file=sys.stderr)
        sys.exit(1)
    out = _output_path(args, "capabilities")
    path = build_capabilities_deck(cases, lib, out, group_by=args.group_by,
                                   template_path=args.template, theme=_theme(args))
    print(f"Created capabilities deck ({len(cases)} cases, grouped by {args.group_by}): {path}")


def cmd_build_tender(args: argparse.Namespace) -> None:
    from .builder import build_tender_deck
    from .kb import filter_cases, load_catalog

    lib = _library_path(args)
    cases = filter_cases(
        load_catalog(lib),
        case_ids=args.cases,
        capabilities=args.capabilities,
        tender_tags=args.tender_tags,
        exclude_confidential=args.exclude_confidential,
    )
    if not cases:
        print("No cases match the given filters.", file=sys.stderr)
        sys.exit(1)
    out = _output_path(args, "tender")
    path = build_tender_deck(cases, lib, out, brief=args.brief or "",
                             template_path=args.template, theme=_theme(args))
    _key_notice(text=True, images=True)
    print(f"Created tender deck ({len(cases)} cases): {path}")


def cmd_build_plan(args: argparse.Namespace) -> None:
    import json

    from .builder import build_plan_deck, split_sections
    from .planner import DESIGN_RULES, PLAN_LAYOUTS, describe_plan, plan_deck, validate_plan

    content_md = Path(args.content).expanduser().read_text(encoding="utf-8")
    sections = split_sections(content_md)
    theme = _theme(args)
    validated, fixes = None, []
    if args.plan:
        try:
            raw = json.loads(Path(args.plan).expanduser().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Can't read --plan {args.plan}: {e}", file=sys.stderr)
            sys.exit(1)
        validated, fixes = validate_plan(sections, raw, theme=theme)

    if args.plan_only:
        planned = validated if validated is not None else plan_deck(
            sections, company=args.company or "", theme=theme)
        print(json.dumps({"rules": DESIGN_RULES, "layouts": list(PLAN_LAYOUTS),
                          "slides": describe_plan(sections, planned), "fixes": fixes},
                         indent=2, ensure_ascii=False))
        return

    out = _output_path(args, "plan")
    path = build_plan_deck(
        title=args.title,
        content_md=content_md,
        subtitle=args.subtitle or "",
        label=args.label or "Plan of Approach",
        output_path=out,
        template_path=args.template,
        enrich=not args.no_enrich,
        company=args.company or "",
        theme=theme,
        slide_plan=validated,
    )
    for fix in fixes:
        print(f"Plan adjustment: {fix}", file=sys.stderr)
    _key_notice(text=validated is None, images=not args.no_enrich)
    print(f"Created plan deck: {path}")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def cmd_list(args: argparse.Namespace) -> None:
    from .kb import filter_cases, load_catalog

    lib = _library_path(args)
    cases = filter_cases(
        load_catalog(lib),
        capabilities=args.capabilities,
        tender_tags=args.tender_tags,
        sector=args.sector,
        client_type=args.client_type,
        status=args.status,
        exclude_confidential=args.exclude_confidential,
    )
    for c in cases:
        print(f"{c['slug']:40s} {c['title']}")
    print(f"\n{len(cases)} case(s) in {lib}")


# ---------------------------------------------------------------------------
# library init / validate
# ---------------------------------------------------------------------------

def cmd_library_init(args: argparse.Namespace) -> None:
    from .kb import rebuild_catalog

    path = Path(args.path).expanduser().resolve()
    (path / "cases").mkdir(parents=True, exist_ok=True)
    (path / "templates").mkdir(parents=True, exist_ok=True)

    template_src = (Path(__file__).parent / "examples" /
                    "sample-library" / "templates" / "case.md")
    template_dest = path / "templates" / "case.md"
    if not template_dest.exists() and template_src.exists():
        template_dest.write_text(template_src.read_text(encoding="utf-8"), encoding="utf-8")

    if not (path / "catalog.json").exists():
        rebuild_catalog(path)

    print(f"Initialized case library at {path}")
    print(f"  - copy {template_dest} into cases/<slug>/case.md to add your first case")
    print(f"  - then run: pandoro deck-mixer library validate {path}")


def cmd_library_validate(args: argparse.Namespace) -> None:
    from .kb import load_catalog, rebuild_catalog

    path = Path(args.path).expanduser().resolve()
    errors: list[str] = []

    if not (path / "cases").is_dir():
        print(f"FAIL — no cases/ directory in {path}")
        sys.exit(1)

    n = rebuild_catalog(path)
    catalog = load_catalog(path)
    for c in catalog["cases"]:
        if not c.get("case_id"):
            errors.append(f"{c['slug']}: missing case_id")
        if len(c.get("sections", [])) < 13:
            errors.append(f"{c['slug']}: only {len(c.get('sections', []))}/13 sections")
        if c.get("confidentiality") not in ("public", "anonymized", "confidential"):
            errors.append(
                f"{c['slug']}: unexpected confidentiality value "
                f"'{c.get('confidentiality')}' (expected public/anonymized/confidential)")
        if not c.get("client"):
            errors.append(f"{c['slug']}: missing client")
        if not c.get("title"):
            errors.append(f"{c['slug']}: missing title")

    if errors:
        print(f"{len(errors)} issue(s) in {path}:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"OK — {n} case(s) valid in {path}")


# ---------------------------------------------------------------------------
# theme init
# ---------------------------------------------------------------------------

def cmd_theme_init(args: argparse.Namespace) -> None:
    import yaml

    from .theme import DEFAULT_THEME, _infer_theme

    path = Path(args.path).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)

    if args.describe:
        theme = _infer_theme(args.describe)
        if theme is None:
            print("Could not infer a theme (no LLM key configured, or the call "
                  "failed) — writing the default theme instead. Configure an "
                  "LLM key, or edit the colors by hand.", file=sys.stderr)
            theme = DEFAULT_THEME
    else:
        theme = DEFAULT_THEME

    def hexs(c) -> str:
        return f"{c:06X}" if isinstance(c, int) else str(c)

    data = {
        "company_name": args.company or theme.company_name,
        "wordmark_text": args.company or theme.wordmark_text,
        "tagline": args.tagline or theme.tagline,
        "website": theme.website,
        "credit": theme.show_credit,
        "colors": {
            "primary": hexs(theme.primary),
            "primary_dark": hexs(theme.primary_dark),
            "accent": hexs(theme.accent),
            "accent_dim": hexs(theme.accent_dim),
            "accent_text": hexs(theme.accent_text),
            "secondary": hexs(theme.secondary),
            "secondary_text": hexs(theme.secondary_text),
            "secondary_soft": hexs(theme.secondary_soft),
        },
        "fonts": {"head": theme.font_head, "body": theme.font_body},
        "mood": list(theme.mood),
        "palette_description": theme.palette_description,
        "assets": {"logo": "logo.png", "favicon": "favicon.png"},
    }
    theme_file = path / "theme.yaml"
    header = (
        "# Deck Mixer theme. Every key is optional; anything left out keeps the default.\n"
        "#   wordmark_text — shown where the logo would go when there is no logo.png\n"
        "#   tagline       — closing-slide headline (empty: company name / logo)\n"
        "#   credit        — small \"Made with Deck Mixer by Growing pAI\" line on the\n"
        "#                   closing slide; set to false to remove it\n"
        "#   colors        — hex, no '#'; *_text variants must read on white\n\n")
    theme_file.write_text(header + yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"Wrote {theme_file}")
    print("  - add logo.png/favicon.png next to it if you have brand assets "
         "(optional — a text wordmark is used otherwise)")
    print(f"  - use it with: --theme {theme_file}")


# ---------------------------------------------------------------------------
# mcp serve
# ---------------------------------------------------------------------------

def cmd_mcp_serve(args: argparse.Namespace) -> None:
    from . import server
    server.mcp.run()


# ---------------------------------------------------------------------------
# skill pack
# ---------------------------------------------------------------------------

def _pyproject_from_metadata() -> dict[str, str]:
    """pyproject.toml (+ README) for vendoring an installed, non-editable pandoro."""
    from importlib.metadata import metadata, requires

    meta = metadata("pandoro")
    deps = [r for r in (requires("pandoro") or []) if "extra ==" not in r]
    pyproject = "\n".join([
        "[build-system]",
        'requires = ["setuptools>=68"]',
        'build-backend = "setuptools.build_meta"',
        "",
        "[project]",
        f'name = "{meta["Name"]}"',
        f'version = "{meta["Version"]}"',
        f'requires-python = "{meta.get("Requires-Python") or ">=3.10"}"',
        "dependencies = [" + ", ".join(f'"{d}"' for d in deps) + "]",
        "",
        "[project.scripts]",
        'pandoro = "pandoro.cli:main"',
        "",
        "[tool.setuptools.packages.find]",
        'include = ["pandoro*", "deck_mixer*"]',
        "",
        "[tool.setuptools.package-data]",
        '"deck_mixer" = ["skill_template/*", "examples/**/*"]',
        "",
    ])
    return {"pyproject.toml": pyproject,
            "README.md": meta.get_payload() or "pandoro deck mixer\n"}


def cmd_skill_pack(args: argparse.Namespace) -> None:
    import zipfile

    template_dir = Path(__file__).parent / "skill_template"
    repo_root = Path(__file__).parent.parent
    out_dir = Path(args.output or ".").expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "deck-mixer-skill.zip"

    # Bundle the engine's own source so `setup.py` can install it locally —
    # pandoro isn't on PyPI yet, so the skill ships the source it installs.
    # From a source checkout ship the real project files; from an installed
    # wheel (site-packages) rebuild a minimal pyproject from the metadata.
    src_files = [f for f in (repo_root / "pyproject.toml", repo_root / "README.md",
                             repo_root / "LICENSE") if f.exists()]
    synthesized = {} if (repo_root / "pyproject.toml").exists() else _pyproject_from_metadata()
    src_packages = ["pandoro", "deck_mixer"]
    skip_dirs = {"__pycache__", "skill_template", "tests", "architecture"}

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(template_dir.iterdir()):
            if f.is_file():
                zf.write(f, arcname=f"deck-mixer/{f.name}")
        for f in src_files:
            zf.write(f, arcname=f"deck-mixer/vendor/pandoro-src/{f.name}")
        for name, text in synthesized.items():
            zf.writestr(f"deck-mixer/vendor/pandoro-src/{name}", text)
        for pkg in src_packages:
            for f in sorted((repo_root / pkg).rglob("*")):
                if f.is_dir() or skip_dirs & set(f.relative_to(repo_root).parts):
                    continue
                rel = f.relative_to(repo_root)
                zf.write(f, arcname=f"deck-mixer/vendor/pandoro-src/{rel}")

    print(f"Wrote {zip_path}")
    print("  - claude.ai / Claude Desktop: Settings > Capabilities > Skills > upload the zip")
    print("  - Claude Code: unzip into ~/.claude/skills/")
    print("  - includes the sample cases only: point it at your own library "
          "and theme via --library/--theme, or a --brand-description")


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------

_CONFIGURABLE_KEYS = (
    "anthropic_api_key", "openai_api_key", "gemini_api_key", "llm_provider",
    "stability_api_key", "together_api_key", "fal_key", "replicate_api_token",
    "image_provider", "image_theme", "image_art_style", "image_prefer_generate",
    "pexels_api_key", "unsplash_access_key",
    "library_path", "theme_path", "brand_description",
    "output_dir", "template_path",
)


def cmd_configure(args: argparse.Namespace) -> None:
    from .config import CONFIG_FILE, inject_keys, load_config, mask, save_config

    updates = {k: v for k, v in vars(args).items() if k in _CONFIGURABLE_KEYS and v is not None}
    if updates:
        save_config(updates)
        print(f"Saved: {', '.join(updates.keys())}\n")

    cfg = load_config()
    print(f"Configuration file: {CONFIG_FILE}")
    for k in _CONFIGURABLE_KEYS:
        v = cfg.get(k)
        display = mask(v) if k.endswith("_key") or k.endswith("_token") else (v or "(not set)")
        print(f"  {k:22s}: {display}")

    from .keys import GEMINI_KEY_URL, has_image_key, has_text_key
    inject_keys()
    if not (has_text_key() and has_image_key()):
        print("\nNo AI key for text and/or images yet — decks will look basic.\n"
              f"One free Gemini key covers both: {GEMINI_KEY_URL}\n"
              "  pandoro deck-mixer configure --gemini-api-key <your key>")


# ---------------------------------------------------------------------------
# argument parser
# ---------------------------------------------------------------------------

def _add_library_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument("--library", help="Path to a case library (default: configured "
                                     "library_path, else the bundled sample library)")


def _add_theme_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--theme", help="Path to a theme.yaml/theme.json")
    p.add_argument("--brand-description", help="Free-text brand description "
                                               "(used if --theme is not set)")
    p.add_argument("--template", help="Path to a .pptx/.potx template file")


def _add_output_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--output-dir", help="Directory to save the .pptx in (default: cwd)")
    p.add_argument("--filename", help="Output filename without extension "
                                      "(default: auto-generated with a timestamp)")


def _leaf(fn):
    """Wrap a leaf command so saved API keys/preferences are loaded into the
    environment right before that command runs (not at parser-build time)."""
    def wrapped(args: argparse.Namespace) -> None:
        from .config import inject_keys
        inject_keys()
        fn(args)
    return wrapped


def register(tool_sub: argparse._SubParsersAction) -> None:
    """Register `deck-mixer` as a subcommand of the umbrella `pandoro` CLI."""
    parser = tool_sub.add_parser(
        "deck-mixer",
        help="Turn a case-study library into branded, editable PPTX decks",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Build a deck")
    build_sub = build.add_subparsers(dest="deck_type", required=True)

    ref = build_sub.add_parser("reference", help="Deep dive on one or more cases")
    _add_library_arg(ref); _add_theme_args(ref); _add_output_args(ref)
    ref.add_argument("--cases", nargs="+", required=True, help="Slug or case_id values")
    ref.set_defaults(func=_leaf(cmd_build_reference))

    caps = build_sub.add_parser("capabilities", help="Portfolio overview grouped by tag")
    _add_library_arg(caps); _add_theme_args(caps); _add_output_args(caps)
    caps.add_argument("--capabilities", nargs="*")
    caps.add_argument("--tender-tags", nargs="*")
    caps.add_argument("--exclude-confidential", action="store_true")
    caps.add_argument("--group-by", choices=("capabilities", "tender_tags"), default="capabilities")
    caps.set_defaults(func=_leaf(cmd_build_capabilities))

    tender = build_sub.add_parser("tender", help="Evidence deck for a tender/pitch")
    _add_library_arg(tender); _add_theme_args(tender); _add_output_args(tender)
    tender.add_argument("--cases", nargs="*")
    tender.add_argument("--capabilities", nargs="*")
    tender.add_argument("--tender-tags", nargs="*")
    tender.add_argument("--exclude-confidential", action="store_true")
    tender.add_argument("--brief", help="Short tender context paragraph")
    tender.set_defaults(func=_leaf(cmd_build_tender))

    plan = build_sub.add_parser("plan", help="Free-form deck from a markdown document")
    _add_theme_args(plan); _add_output_args(plan)
    plan.add_argument("--title", required=True, help="Cover slide title (use \\n for line breaks)")
    plan.add_argument("--content", required=True, help="Path to a markdown file "
                                                        "(H2 headings drive slides)")
    plan.add_argument("--subtitle")
    plan.add_argument("--label", help='Small label above the title (default: "Plan of Approach")')
    plan.add_argument("--company", help="Client/company name, for planner tone")
    plan.add_argument("--no-enrich", action="store_true",
                      help="Skip fetching images (image slots stay placeholders)")
    plan.add_argument("--plan", help="JSON slide plan to use instead of the planner "
                                     "(the 'slides' list from --plan-only, edited)")
    plan.add_argument("--plan-only", action="store_true",
                      help="Print the slide plan (and the design rules) as JSON; build nothing")
    plan.set_defaults(func=_leaf(cmd_build_plan))

    lst = sub.add_parser("list", help="List cases in a library")
    _add_library_arg(lst)
    lst.add_argument("--capabilities", nargs="*")
    lst.add_argument("--tender-tags", nargs="*")
    lst.add_argument("--sector")
    lst.add_argument("--client-type")
    lst.add_argument("--status")
    lst.add_argument("--exclude-confidential", action="store_true")
    lst.set_defaults(func=_leaf(cmd_list))

    library = sub.add_parser("library", help="Manage case libraries")
    library_sub = library.add_subparsers(dest="library_command", required=True)

    lib_init = library_sub.add_parser("init", help="Scaffold a new case library")
    lib_init.add_argument("path")
    lib_init.set_defaults(func=_leaf(cmd_library_init))

    lib_validate = library_sub.add_parser("validate", help="Lint a case library")
    lib_validate.add_argument("path")
    lib_validate.set_defaults(func=_leaf(cmd_library_validate))

    theme = sub.add_parser("theme", help="Manage brand themes")
    theme_sub = theme.add_subparsers(dest="theme_command", required=True)

    theme_init = theme_sub.add_parser("init", help="Scaffold a theme.yaml")
    theme_init.add_argument("path", help="Directory to write theme.yaml into")
    theme_init.add_argument("--describe", help="Free-text brand description to "
                                               "infer a palette from (requires an LLM key)")
    theme_init.add_argument("--company")
    theme_init.add_argument("--tagline")
    theme_init.set_defaults(func=_leaf(cmd_theme_init))

    mcp_p = sub.add_parser("mcp", help="Run pandoro as an MCP server")
    mcp_sub = mcp_p.add_subparsers(dest="mcp_command", required=True)
    mcp_serve = mcp_sub.add_parser("serve", help="Start the MCP server (stdio)")
    mcp_serve.set_defaults(func=_leaf(cmd_mcp_serve))

    skill = sub.add_parser("skill", help="Package pandoro as a Claude Skill")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    skill_pack = skill_sub.add_parser("pack", help="Write a deck-mixer-skill.zip "
                                                    "(engine only — no library/theme)")
    skill_pack.add_argument("--output", help="Directory to write the zip into (default: cwd)")
    skill_pack.set_defaults(func=_leaf(cmd_skill_pack))

    cfg = sub.add_parser("configure", help="Save API keys and preferences")
    for key in _CONFIGURABLE_KEYS:
        cfg.add_argument(f"--{key.replace('_', '-')}", dest=key)
    cfg.set_defaults(func=_leaf(cmd_configure))
