"""Pandoro CLI — dispatches to each tool's subcommands.

Currently ships one tool, `deck-mixer` (turn a case-study library into
branded PPTX decks). See deck_mixer/cli.py.
"""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pandoro",
        description="Pandoro — a toolbox of Growing pAI tools.",
    )
    tool_sub = parser.add_subparsers(dest="tool", required=True)

    from deck_mixer.cli import register as register_deck_mixer
    register_deck_mixer(tool_sub)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
