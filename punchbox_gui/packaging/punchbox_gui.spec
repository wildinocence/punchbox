# -*- mode: python ; coding: utf-8 -*-
#
# Build the punchbox-gui Windows executable. Run from the repo root on
# Windows, in the same environment as the [gui] extras:
#
#   pip install pyinstaller
#   pyinstaller punchbox_gui\packaging\punchbox_gui.spec
#
# Produces dist\punchbox-gui\ (a folder, --onedir) - launch
# dist\punchbox-gui\punchbox-gui.exe. --onedir is deliberate: a single-file
# --onefile build has to self-extract oemer's onnxruntime + model weights on
# every launch, which is slow given their size - stick with --onedir until
# that's a real problem, then wrap this folder in an installer instead.
#
# Before building, run `oemer` once on any image so its model weights (which
# it downloads into its own installed package directory on first use, not
# shipped in the pip package) are already on disk - collect_data_files below
# then bundles them automatically, so the shipped app doesn't need its own
# first-run download.

import os

from PyInstaller.utils.hooks import collect_data_files

# Every path here - the entry script below, and these data-file sources - is
# resolved relative to SPECPATH (this file's own directory), not whatever the
# current working directory was when `pyinstaller` was invoked - confirmed by
# actually running this spec, which failed on both until made explicit.
repo_root = os.path.join(SPECPATH, "..", "..")

# sounddevice is a single .py module, not a package - collect_data_files()
# requires a package and just warns and skips otherwise (confirmed by
# actually running this spec). Its PortAudio binary is bundled automatically
# by pyinstaller-hooks-contrib's own sounddevice hook instead; nothing to do
# here for it.
datas = [(os.path.join(repo_root, "punchbox.yaml"), ".")]
datas += collect_data_files("oemer")  # picks up model weights if already cached - see above
datas += collect_data_files("music21")  # its converter needs some bundled metadata/config

hiddenimports = [
    # A separate Qt module from Widgets/Gui/Core - easy to miss since nothing
    # imports it directly by name outside punchbox_gui/print_export.
    "PySide6.QtPrintSupport",
]

app_script = os.path.join(SPECPATH, "..", "app.py")

a = Analysis(
    [app_script],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="punchbox-gui",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="punchbox-gui",
)
