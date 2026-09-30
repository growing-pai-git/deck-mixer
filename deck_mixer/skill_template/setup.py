"""Install pandoro into a local .venv next to this file. Safe to re-run.

    python3 setup.py        (Windows: py setup.py)

Prints the full path of the `pandoro` command to use for everything else.
Works on macOS, Linux and Windows, and in Claude's code-execution sandbox.
"""

import subprocess
import sys
import venv
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
BIN = VENV / ("Scripts" if sys.platform == "win32" else "bin")
PYTHON = BIN / ("python.exe" if sys.platform == "win32" else "python")
PANDORO = BIN / ("pandoro.exe" if sys.platform == "win32" else "pandoro")
SAMPLE = HERE / "vendor" / "pandoro-src" / "deck_mixer" / "examples" / "sample-library"


def main() -> None:
    if sys.version_info < (3, 10):
        sys.exit(f"Python 3.10+ is required (found {sys.version.split()[0]}).")
    if not PYTHON.exists():
        venv.create(VENV, with_pip=True)
    pip = [str(PYTHON), "-m", "pip", "install", "-q", "--disable-pip-version-check"]
    try:
        subprocess.run(pip + ["--upgrade", "pip"], check=True)
        subprocess.run(pip + [str(HERE / "vendor" / "pandoro-src")], check=True)
    except subprocess.CalledProcessError:
        sys.exit("Installing pandoro's dependencies failed. If this runs in a sandbox, "
                 "package downloads (pypi.org) may be blocked by its network settings.")
    print("pandoro installed.")
    print(f"PANDORO={PANDORO}")
    print(f"SAMPLE_LIBRARY={SAMPLE}")


if __name__ == "__main__":
    main()
