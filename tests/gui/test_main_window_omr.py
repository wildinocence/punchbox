import time

import pytest

pytest.importorskip("PySide6")
fitz = pytest.importorskip("fitz")
music21 = pytest.importorskip("music21")

from PySide6.QtCore import QCoreApplication  # noqa: E402

from punchbox_gui.main_window import MainWindow  # noqa: E402
from punchbox_gui.omr.oemer_engine import OemerEngine  # noqa: E402


def _make_pdf(path):
    doc = fitz.open()
    doc.new_page(width=200, height=300)
    doc.save(str(path))
    doc.close()


def _write_musicxml(path, pitches, lyrics=None):
    part = music21.stream.Part()
    for i, pitch_name in enumerate(pitches):
        n = music21.note.Note(pitch_name, quarterLength=1.0)
        if lyrics:
            n.lyric = lyrics[i]
        part.append(n)
    score = music21.stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))
    return path


def _pump_until(condition, timeout_s=5.0):
    """Process Qt events until `condition()` is true or timeout - used instead
    of a real user click-and-wait since OMR runs on a background QThread.
    """
    deadline = time.monotonic() + timeout_s
    while not condition() and time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


@pytest.fixture(autouse=True)
def _no_blocking_dialogs(monkeypatch):
    # QMessageBox.critical()/.warning() are modal - calling the real ones here
    # would hang the test forever waiting for a button click that can never
    # come under the offscreen platform. Every test in this module gets this
    # patched automatically so a bug that accidentally triggers one fails
    # loudly (via the recorded call) instead of hanging the whole suite.
    calls = []
    monkeypatch.setattr(
        "punchbox_gui.main_window.QMessageBox.critical",
        lambda *a, **k: calls.append(("critical", a)),
    )
    monkeypatch.setattr(
        "punchbox_gui.main_window.QMessageBox.warning",
        lambda *a, **k: calls.append(("warning", a)),
    )
    return calls


def _wait_for_omr_to_finish(window):
    _pump_until(lambda: window._omr_worker is None or not window._omr_thread.isRunning())


def test_open_pdf_loads_recognized_notes_into_state(
    tmp_path, qapp, monkeypatch, _no_blocking_dialogs
):
    pdf_path = tmp_path / "song.pdf"
    _make_pdf(pdf_path)
    xml_path = _write_musicxml(tmp_path / "out.musicxml", ["C4", "D4", "E4"], ["A", "men", None])

    monkeypatch.setattr(OemerEngine, "recognize_page", lambda self, image_path, out: xml_path)
    monkeypatch.setattr(
        "punchbox_gui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(pdf_path), ""),
    )

    window = MainWindow("punchbox.yaml")
    window._open_pdf()
    _wait_for_omr_to_finish(window)

    assert _no_blocking_dialogs == []
    assert [n.pitch for n in window.state.tune.sorted_notes()] == [60, 62, 64]
    assert [n.lyric for n in window.state.tune.sorted_notes()] == ["A", "men", None]
    assert window.state.tune.title == "song"
    assert any("review" in w.lower() for w in window.state.tune.warnings)


def test_open_pdf_reports_engine_failure_without_crashing(
    tmp_path, qapp, monkeypatch, _no_blocking_dialogs
):
    pdf_path = tmp_path / "song.pdf"
    _make_pdf(pdf_path)

    def fake_recognize_page(self, image_path, output_dir):
        raise RuntimeError("simulated OMR failure")

    monkeypatch.setattr(OemerEngine, "recognize_page", fake_recognize_page)
    monkeypatch.setattr(
        "punchbox_gui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(pdf_path), ""),
    )

    window = MainWindow("punchbox.yaml")
    original_notes = list(window.state.tune.notes)

    window._open_pdf()
    _wait_for_omr_to_finish(window)

    assert [c[0] for c in _no_blocking_dialogs] == ["critical"]
    # a failed recognition must not corrupt the currently open tune
    assert window.state.tune.notes == original_notes


def test_open_pdf_missing_file_reports_failure(tmp_path, qapp, monkeypatch, _no_blocking_dialogs):
    monkeypatch.setattr(
        "punchbox_gui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(tmp_path / "does_not_exist.pdf"), ""),
    )

    window = MainWindow("punchbox.yaml")
    window._open_pdf()
    _wait_for_omr_to_finish(window)

    assert [c[0] for c in _no_blocking_dialogs] == ["critical"]
