"""Build dist/deck-mixer-<version>.mcpb (Claude Desktop extension bundle).

Stages the bundle layout in build/mcpb/:
    manifest.json        <- mcpb/manifest.json (version synced to pyproject.toml)
    pyproject.toml       <- dependencies only; Claude Desktop installs them with uv
    server/main.py       <- mcpb/main.py
    server/deck_mixer/   <- the engine, without tests, diagrams or the skill template
    LICENSE
then packs it with the official mcpb CLI (needs Node.js for `npx`).

Usage, from the project root (Python 3.11+):
    python mcpb/build.py
"""

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "build" / "mcpb"


def main() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    deps = project["dependencies"] + project["optional-dependencies"]["mcp"]

    shutil.rmtree(STAGE, ignore_errors=True)
    (STAGE / "server").mkdir(parents=True)

    manifest = json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8"))
    manifest["version"] = version
    (STAGE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    dep_lines = "".join(f'    "{d}",\n' for d in deps)
    (STAGE / "pyproject.toml").write_text(
        "[project]\n"
        'name = "deck-mixer-mcpb"\n'
        f'version = "{version}"\n'
        f'requires-python = "{project["requires-python"]}"\n'
        f"dependencies = [\n{dep_lines}]\n",
        encoding="utf-8",
    )

    shutil.copy(ROOT / "mcpb" / "main.py", STAGE / "server" / "main.py")
    shutil.copytree(ROOT / "deck_mixer", STAGE / "server" / "deck_mixer",
                    ignore=shutil.ignore_patterns("tests", "architecture", "skill_template",
                                                  "__pycache__", "*.pyc"))
    shutil.copy(ROOT / "LICENSE", STAGE / "LICENSE")

    output = ROOT / "dist" / f"deck-mixer-{version}.mcpb"
    output.parent.mkdir(exist_ok=True)
    npx = shutil.which("npx")
    if not npx:
        sys.exit("npx not found — install Node.js to pack the bundle.")
    subprocess.run([npx, "-y", "@anthropic-ai/mcpb", "pack", str(STAGE), str(output)], check=True)
    print(f"\nBundle written to {output}")


if __name__ == "__main__":
    main()
