"""Build the punchbox-gui executable via PyInstaller.

Run from the repo root:
    python punchbox_gui/packaging/build.py

Requires `pip install pyinstaller` in the same environment as the [gui]
extras (`pip install -e .[gui]`). Keeping the exact invocation here instead
of leaving it as tribal knowledge - PyInstaller flag combinations are fragile
and easy to silently regress.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_PATH = Path(__file__).resolve().parent / "punchbox_gui.spec"


def main():
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_PATH), "--noconfirm"],
        cwd=REPO_ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
