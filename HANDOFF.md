# Punchbox — Project Handoff / Session Summary

Written to hand this project off to a new session/repository. Covers the goal, every domain fact
discovered along the way, what was built phase by phase, real bugs found and fixed, and what's
still open. If you're a fresh Claude session reading this: read it fully before touching code —
several of the "obvious" design choices below only make sense in light of a mistake that was
already made and fixed once.

## The goal

Turn `punchbox` (a small Python 2 CLI that converts a MIDI file into an SVG punch-strip template)
into a Windows 11 desktop app for a real **30-note hand-crank music box**. The app should:

1. Read sheet-music **PDFs from jw.org** and automatically recognize the notes (OMR — optical
   music recognition), not require a MIDI file.
2. Let the user **compose/edit notes directly** in a piano-roll editor.
3. Play a **real-time audio preview** of how the tune will sound on the actual box.
4. **Print** the finished punch-strip design directly to a physical printer (an Epson EcoTank
   ET-2862).

## Key domain facts (don't re-derive these — they're settled)

- **The physical strip is 90mm wide x ~700mm long**, one continuous run fed through the box in one
  direction — *not* A4 pages to cut and tape together. This was confirmed against a photo of the
  user's real strip template (30 note-name columns across the width, time running down the
  length, feed-direction arrow at the top).
- **The 30-note pitch mapping** was read from that same photo (careful zoomed reading of two
  interleaved rows of note-name labels — commercial strips print labels in 2 staggered rows
  because 30 lanes are too narrow for 30 side-by-side labels), then cross-validated two
  independent ways: against a published reference chart for 30-note DIY music-box mechanisms
  (miium.com), and — this was a pleasant surprise — it turned out to be an *exact* match for an
  array that was already sitting in this repo's `punchbox.yaml` under a mislabeled key (`35note`
  instead of `30note`). The array itself needed no changes, just the key rename. Final mapping:
  `[60, 62, 67, 69, 71, 72, 74, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92,
  93, 94, 95, 96, 98, 100]`, `pitch: 2.0`, `reverse: True`.
- **jw.org offers PDF sheet music, not MIDI.** Two relevant PDF formats exist per songbook: the
  main songbook (piano arrangement, chords stacked in two staves — messy for OMR) and a
  **"Partitura de [songbook name]"** edition, which is a single monophonic melody line with chord
  symbols and lyrics — much cleaner for OMR, and it's the whole songbook as one PDF (one page or
  so per song), not per-song files. Always prefer the "Partitura" edition as OMR input.
- **The physical strip feed rate (mm/s) has never been measured** on the user's real box. It's a
  placeholder config value (`feed_rate_mm_per_s: 15.0`) with a GUI override slider. Needs a
  stopwatch and the real hardware to calibrate properly.
- **Printer is an Epson EcoTank ET-2862**, a standard consumer inkjet — ordinary Windows printing
  applies, no special protocol, but a ~700mm custom page length is untested; the printer driver
  may or may not offer a custom paper size that long. Unverified.

## Architecture

Two packages in one repo:

- `punchbox/` — headless core library, zero Qt/audio/OMR dependencies, importable and testable on
  its own. Also the original CLI (`punchbox` command).
- `punchbox_gui/` — the PySide6 desktop app, installed via the `gui` extra
  (`pip install -e .[gui]`).

The single most important architectural decision: **`punchbox/layout.py`'s `draw_layout()` is the
one and only place punch-strip geometry gets computed**, driven through a small `Renderer`
protocol (`punchbox/renderer.py`: `new_page`, `line`, `circle`, `text`, `save`). Every output
target — SVG export, on-screen live preview, printing — is just a different `Renderer`
implementation calling the *same* `draw_layout()`. This is why the live piano-roll editor is
guaranteed to show exactly what will print: there's structurally only one geometry implementation,
not three kept in sync by hand.

`draw_layout()`'s own coordinate convention is landscape: x = time (spans `page_width`), y = note
lane (spans `page_height`, stacking multiple staves if a page isn't tall enough for a whole tune).
This is backwards from the real strip's shape (narrow across notes, long along time), so a
`RotatedRenderer` (in `punchbox/renderer.py`) wraps any other `Renderer` and swaps x/y — used by
print and SVG export, *not* by the live editor (which deliberately stays landscape — horizontal-
scrolling time reads better on a normal monitor while composing).

```
punchbox/
  model.py          NoteEvent (pitch, start, duration, source, lyric, id), Tune
  notes.py          note_name() / NOTE_NAMES
  config.py         MusicBox (note_data, pitch, reverse, note_collision, feed_rate_mm_per_s)
  midi_source.py     load_tune_from_midi()
  transpose.py       find_best_transpose() / TransposeResult
  layout.py           draw_layout(), compute_stave_geometry(), nearest_lane(),
                       scene_point_to_note(), stave_position_for_time_mm()
  renderer.py         Renderer ABC, RotatedRenderer
  render_svg.py       SvgRenderer(Renderer)
  cli.py              the original `punchbox` CLI command

punchbox_gui/
  state.py            AppState(QObject) - single shared tune/box/params, mutated only via
                       add_note/move_note/delete_notes/set_tune/set_music_box/set_layout_params
  main_window.py       wires every panel to AppState; owns AudioEngine and OMR worker lifecycle
  app.py               entry point (punchbox-gui console script / PyInstaller target)
  editor/
    scene_renderer.py  Renderer -> QGraphicsScene (the live preview)
    note_item.py        draggable/selectable QGraphicsEllipseItem per note
    piano_roll_view.py  click-to-add, drag-to-move, Delete-to-remove, playhead
  print_export/
    qt_painter_renderer.py  Renderer -> QPainter (print + preview)
    print_controller.py     QPrinter setup, calibration-ruler diagnostic page
  audio/
    synth.py            render_tine_pluck() - numpy synthesis of the box's actual timbre
    engine.py            AudioEngine - pre-rendered PCM buffer, sounddevice.OutputStream playback
  omr/
    engine_base.py       OMREngine ABC ("run a process, read back a MusicXML file")
    oemer_engine.py       shells out to the `oemer` CLI
    pdf_raster.py          PyMuPDF: PDF -> per-page PNGs
    musicxml_to_tune.py    music21 Score -> Tune (part selection, lyric extraction, page merging)
    omr_worker.py           QThread wrapper (progress/cancel signals)
  packaging/
    punchbox_gui.spec        PyInstaller spec (--onedir)
    build.py                  wraps the exact `pyinstaller` invocation
```

## What's done, phase by phase

**Phase 1 — Python 3 core library.** Split the Python 2 `punchbox/__init__.py` into the modules
above. Switched the canonical time unit from MIDI ticks to quarter-length beats (MIDI ticks are
file-specific; OMR/music21 has no concept of them at all). Fixed real Python 2→3 bugs:
`yaml.load`→`safe_load`, `dict.iteritems()`→`.items()`, and an integer-division bug in
`note_name()` that produced broken names like `"C#3.0833333333333335"` under Python 3 (needed
`//` not `/`). Renamed `punchbox.yaml`'s `35note` boxen key to `30note` (see above).

**Phase 2 — PySide6 GUI skeleton**, MIDI-only at this point (no OMR yet). `AppState`, a read-only
`QGraphicsScene` piano-roll preview, exact-mm-scale printing via `QPrinter`
(`setFullPage(True)`, no fit-to-page), a one-click 100mm calibration-ruler printout for verifying
a real printer isn't silently rescaling. **Two real `QPainter` bugs found here, both worth
remembering if text mysteriously doesn't render or renders huge:**
  1. `QPainter.drawText(QRectF, str)` (the rect-based overload, no explicit alignment flags)
     silently draws nothing if the rect is smaller than the font's natural line box. Fix: use the
     point-based `drawText(QPointF, str)` overload (baseline-positioned, matches svgwrite's `insert`
     convention) instead.
  2. `QFont` point size is a physical unit (1/72in) that then gets **multiplied again** by
     whatever `painter.scale()` transform is active — so text sized naively (e.g.
     `font_size_mm * 2.83` to convert mm→pt) renders `resolution/72` times too large. Fix:
     pre-shrink by the inverse of that factor: `point_size = mm_height * (72/25.4) / dots_per_mm`.
     See `QPainterRenderer.text()` for the working implementation.

**Phase 3 — Piano-roll editing.** Click an empty lane to add a note, drag to move (snaps to lane
+ click position in time), select + Delete to remove — all funneled through
`AppState.add_note/move_note/delete_notes`. `layout.py` gained `compute_stave_geometry()`
(extracted from `draw_layout`, also now guarantees at least one page/stave even for an empty tune
so there's something to click) and `scene_point_to_note()` (the exact inverse of `draw_layout`'s
dot placement). **Real bug found via QTest-simulated click/drag interaction tests (not just unit
tests):** adding a single manual note re-ran the MIDI-import auto-transpose search over the
now-changed tune, and via the deliberately-preserved "last exact match wins" tie-break (kept from
the original Python 2 code for MIDI-import fidelity), could silently retranspose and jump the
note you just placed to a different lane. Fixed: `AppState` now locks the transpose shift the
moment manual editing starts (`_lock_transpose()`), only resetting on a fresh `set_tune()` —
auto-transpose search is for fitting *imported* music to the box's range, not for composing
directly on the box's own lanes.

**Paper-size correction** (came after Phase 4, prompted by the user clarifying the physical
format wasn't A4): added `RotatedRenderer` (see Architecture above), updated `punchbox.yaml`'s
`page.width`/`page.height`/`margin`/`marker_size` for the real 90x700mm strip. Verified with a
real CLI run — the emitted SVG measures exactly 90.0mm x 700.0mm and visually matches the user's
reference photo.

**Phase 4 — Audio preview.** `render_tine_pluck()` synthesizes the box's actual plucked-comb
timbre with numpy (fundamental + quiet 2nd harmonic under a fixed exponential decay) — explicitly
*not* a generic MIDI/piano soundfont voice, and the envelope is fixed regardless of any note's
"duration" (a real plucked tine's decay is a physical property of the comb, not something the
source notation controls). `AudioEngine.build_buffer()` pre-renders the whole tune to one PCM
buffer, placing each note via the same `nearest_lane()` snapping the visual dots use (so preview
audio always matches what will print), converted mm→seconds via `feed_rate_mm_per_s`. Playback
uses a single `sounddevice.OutputStream` with a read-pointer callback (`read_chunk()`) rather than
sounddevice's simple `play()`/`stop()` helpers, so pause/seek just move where the callback reads
from. A `finished_callback` clears `self._stream` when playback ends naturally — without it,
`is_playing()` would keep reporting `True` forever after a tune finishes on its own. A playhead
line (`stave_position_for_time_mm()`, the inverse of `draw_layout`'s per-stave time offset) tracks
position in the piano-roll during playback via a `QTimer`.

**Phase 5 — OMR pipeline.** "Open PDF (OMR)…" → `pdf_raster.rasterize_pdf()` (PyMuPDF, ~300dpi) →
`OemerEngine.recognize_page()` shells out to the `oemer` CLI per page (its *only* public
interface; output naming convention `{image-basename}.musicxml` was confirmed by reading oemer's
own source, not guessed) → `music21.converter.parse()` → `musicxml_to_tune.build_tune_from_pages()`
stitches per-page note lists into one `Tune`, offsetting each page by the running end-time of
every page before it (OMR has no concept of a PDF-wide timeline, only per-page images — merging
happens on our own `NoteEvent` lists, not by combining music21 `Score` objects). Chords explode
into one `NoteEvent` per pitch rather than collapsing to the top note. Runs on a background
`QThread` (`OmrWorker`) with progress/cancel signals. A **required** part-picker dialog appears
when a score has more than one part (jw.org's main songbook format has this; the "Partitura"
format usually doesn't). Every OMR-built `Tune` carries an unconditional "review before printing"
warning — OMR accuracy is inherently imperfect (true even for more mature engines than `oemer`),
so the Phase-3 piano-roll editing is the *required* safety net here, not optional polish.

**Fixed requirement (explicitly requested by the user): lyric placement must never land on a
punched hole.** `music21` notes carry a `.lyric` (from MusicXML `<lyric>`); it's copied into
`NoteEvent.lyric`. `draw_layout()` renders it at `line_offset - font_size` — strictly above the
topmost lane's y-coordinate, which by construction can never equal any lane's y (`line_offset +
lane*pitch` for `lane >= 0`). Verified two ways: a direct geometry test asserting the lyric y-set
and the lane y-set are disjoint, and visually via a real rendered SVG.

**Phase 7 (packaging) groundwork** — started but not finished. `punchbox_gui/packaging/` has a
working PyInstaller spec + build script. Actually *running* the build (even though this
sandbox is Linux, so it produces a Linux binary, not a Windows one — but `Analysis`/dependency
resolution and a runtime smoke test are platform-independent) found and fixed two more real bugs:
  1. `app.py` used a relative import (`from .main_window import MainWindow`), which breaks once
     PyInstaller freezes it as the top-level entry script (runs as `__main__`, not as part of the
     `punchbox_gui` package). Fixed: absolute import instead.
  2. `MainWindow` loaded `punchbox.yaml` via a plain cwd-relative path — fine for `python -m
     punchbox_gui.app` run from the repo root, broken for a shipped .exe launched from the Start
     Menu/Desktop (wrong cwd). Fixed: `app.py` now resolves the bundled copy via `sys._MEIPASS`
     when frozen, falling back to cwd in normal dev runs.
  3. (Documented, not a bug) every path in a `.spec` file resolves relative to the spec file's own
     directory (`SPECPATH`), not the directory `pyinstaller` was invoked from.
  4. (Documented, not a bug) `sounddevice` is a single `.py` module, not a package —
     `collect_data_files()` silently skips it; its PortAudio DLL comes from
     `pyinstaller-hooks-contrib`'s own hook instead, nothing to do manually.

## What's NOT done / open

- **Phase 6 (boxen/config editor GUI)** — never started. Right now `punchbox.yaml` is hand-edited;
  there's no in-app UI for adding/editing a music-box definition.
- **Phase 7 (packaging) isn't finished** — the spec builds and the Linux smoke test passes, but
  the actual Windows `.exe` has never been built or run. Expect more hidden-import/DLL issues
  specific to Windows that a Linux build can't surface (PySide6's Windows platform plugin,
  onnxruntime's Windows DLLs, etc.).
- **`oemer`'s real OMR accuracy has never been validated** against an actual jw.org PDF. This
  session's sandbox blocks GitHub release-asset downloads (org egress policy, not a product
  issue), and `oemer`'s model weights download from GitHub on first run — so the model itself
  could never actually run here. Everything in the OMR pipeline *around* the model (rasterizing,
  MusicXML parsing, page-merging, part selection, lyric extraction, worker threading) was tested
  thoroughly with a fake OMR engine standing in for `oemer`, but "does `oemer` actually read a
  real hymn page correctly" is completely unverified. This is the single biggest remaining
  unknown in the whole project — validate it early on real hardware, since a bad answer here
  might mean revisiting the OMR engine choice (e.g. Audiveris, AGPL-licensed, more mature, JVM-
  based — was considered and deferred in favor of `oemer`'s simpler no-JVM packaging, but never
  actually compared head to head).
- **No real printer test.** The calibration-ruler diagnostic exists but has never been printed on
  the actual ET-2862. Whether the printer driver even offers a ~700mm custom page length at all is
  unknown.
- **No real audio hardware test.** `AudioEngine.build_buffer()`/`read_chunk()`/seek/pause logic is
  thoroughly unit-tested, but `sounddevice.OutputStream` was never opened against a real audio
  device (this sandbox has zero — confirmed via `sd.query_devices()` returning empty). The
  `finished_callback`/thread-safety design (see Phase 4 above) is reasoned through carefully but
  unverified in practice.
- **`feed_rate_mm_per_s` is an unmeasured placeholder** (15.0). Needs a stopwatch and the real box.
- Everything above is tracked more precisely as inline code comments/docstrings at the relevant
  call sites — search for "unverified", "unmeasured", or "needs the user's" in the codebase if
  something here is unclear.

## Testing approach (why it caught 6+ real bugs instead of 0)

The whole project leaned hard on **exercising real behavior instead of mocking it out**, wherever
the sandbox allowed: `QTest`-simulated mouse clicks/drags/key presses driving the actual
`PianoRollView` wired to a real `AppState` (not just calling internal methods directly); rendering
to a real `QPrinter` pointed at a PDF file and checking actual text content via PyMuPDF (not just
"did a file get created"); `music21` round-tripping real `.musicxml` files written to disk (not
just in-memory `Score` objects); a real background `QThread` for the OMR worker tests; actually
running the PyInstaller build rather than just writing a plausible-looking spec file. Every one of
the "real bug found" notes above was caught this way, not by code review. Keep doing this in
whatever comes next — the parts of this codebase that were *only* eyeballed (nothing comes to mind
that wasn't eventually exercised somehow, but if you add new code, exercise it for real) are the
riskiest.

Run the suite with `QT_QPA_PLATFORM=offscreen python -m pytest tests/` (offscreen avoids needing a
real display; GUI/audio/OMR tests skip cleanly via `pytest.importorskip` if their extras aren't
installed, so the core `tests/` suite has zero Qt/audio/OMR dependency). 88/88 passing as of this
handoff.

One meta-lesson from debugging a test hang along the way: **never let a real modal dialog
(`QMessageBox.critical/.warning`, etc.) fire unmocked in a headless/offscreen test** — it blocks
forever waiting for a button click that can never come. Every test that can reach an error path
which shows one needs that dialog call mocked first.

## Setup

```
git clone <repo-url> punchbox
cd punchbox
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -U pip
pip install -e .[gui]
python -m punchbox_gui.app                            # run from the repo root
```

CLI-only (no GUI deps needed): `pip install -e .` then `punchbox <file.mid>`.
