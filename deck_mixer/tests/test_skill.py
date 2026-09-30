"""The packed Claude Skill: cross-platform setup, sample cases included, no
tests, diagrams or stale bash-only instructions."""

from __future__ import annotations

import argparse
import zipfile


def test_skill_pack_contents(tmp_path):
    from pathlib import Path
    from deck_mixer.cli import cmd_skill_pack

    # an installed copy has bytecode caches next to the template files
    cache = Path(__file__).parents[1] / "skill_template" / "__pycache__"
    cache.mkdir(exist_ok=True)
    cmd_skill_pack(argparse.Namespace(output=str(tmp_path)))
    names = zipfile.ZipFile(tmp_path / "deck-mixer-skill.zip").namelist()

    assert "deck-mixer/SKILL.md" in names
    assert "deck-mixer/setup.py" in names
    assert "deck-mixer/setup.sh" not in names
    src = "deck-mixer/vendor/pandoro-src/"
    assert src + "pyproject.toml" in names
    assert src + "deck_mixer/examples/sample-library/catalog.json" in names
    assert not [n for n in names if "/tests/" in n or "/architecture/" in n
                or "__pycache__" in n]

    skill = zipfile.ZipFile(tmp_path / "deck-mixer-skill.zip").read("deck-mixer/SKILL.md").decode()
    assert "setup.py" in skill and ".venv/bin" not in skill and "setup.sh" not in skill
