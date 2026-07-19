import pytest

pytest.importorskip("PySide6")
music21 = pytest.importorskip("music21")

from PySide6.QtCore import QEventLoop  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402

from punchbox_gui.omr.omr_worker import OmrWorker  # noqa: E402
from punchbox_gui.omr.omr_worker import run_omr_in_background  # noqa: E402


def _write_musicxml(path, pitch="C4"):
    part = music21.stream.Part()
    part.append(music21.note.Note(pitch, quarterLength=1.0))
    score = music21.stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))
    return path


class FakeEngine:
    def __init__(self, musicxml_paths):
        self._paths = iter(musicxml_paths)
        self.calls = []

    def recognize_page(self, image_path, output_dir):
        self.calls.append(image_path)
        return next(self._paths)


def test_run_emits_progress_and_scores_ready(tmp_path, qapp, monkeypatch):
    page_paths = [tmp_path / "page000.png", tmp_path / "page001.png"]
    for p in page_paths:
        p.write_bytes(b"fake")
    xml_paths = [_write_musicxml(tmp_path / "page{:03d}.musicxml".format(i)) for i in range(2)]

    monkeypatch.setattr(
        "punchbox_gui.omr.omr_worker.rasterize_pdf", lambda pdf_path, dpi=300: page_paths
    )

    worker = OmrWorker("fake.pdf", engine=FakeEngine(xml_paths))

    progress_calls = []
    worker.progress.connect(lambda c, t, m: progress_calls.append((c, t, m)))
    scores_result = []
    worker.scoresReady.connect(lambda scores: scores_result.append(scores))
    failures = []
    worker.failed.connect(lambda msg: failures.append(msg))

    worker.run()

    assert failures == []
    assert len(scores_result) == 1
    assert len(scores_result[0]) == 2
    assert len(progress_calls) == 3  # one per page + final "Done"
    assert progress_calls[-1] == (2, 2, "Done")


def test_run_emits_failed_on_engine_error(tmp_path, qapp, monkeypatch):
    page_paths = [tmp_path / "page000.png"]
    page_paths[0].write_bytes(b"fake")
    monkeypatch.setattr(
        "punchbox_gui.omr.omr_worker.rasterize_pdf", lambda pdf_path, dpi=300: page_paths
    )

    class BrokenEngine:
        def recognize_page(self, image_path, output_dir):
            raise RuntimeError("oemer exploded")

    worker = OmrWorker("fake.pdf", engine=BrokenEngine())
    failures = []
    worker.failed.connect(lambda msg: failures.append(msg))
    scores_result = []
    worker.scoresReady.connect(lambda scores: scores_result.append(scores))

    worker.run()

    assert scores_result == []
    assert failures == ["oemer exploded"]


def test_run_stops_early_when_cancelled(tmp_path, qapp, monkeypatch):
    page_paths = [tmp_path / "page{:03d}.png".format(i) for i in range(5)]
    for p in page_paths:
        p.write_bytes(b"fake")
    monkeypatch.setattr(
        "punchbox_gui.omr.omr_worker.rasterize_pdf", lambda pdf_path, dpi=300: page_paths
    )

    worker = OmrWorker("fake.pdf")

    class CountingEngine:
        def __init__(self):
            self.calls = 0

        def recognize_page(self, image_path, output_dir):
            self.calls += 1
            if self.calls == 2:
                worker.cancel()
            return _write_musicxml(image_path.with_suffix(".musicxml"))

    engine = CountingEngine()
    worker.engine = engine

    scores_result = []
    worker.scoresReady.connect(lambda scores: scores_result.append(scores))
    failures = []
    worker.failed.connect(lambda msg: failures.append(msg))

    worker.run()

    assert scores_result == []
    assert failures == []
    assert engine.calls == 2  # stopped right after the cancel, not all 5 pages


def test_run_omr_in_background_delivers_scores_via_a_real_thread(tmp_path, qapp, monkeypatch):
    page_paths = [tmp_path / "page000.png"]
    page_paths[0].write_bytes(b"fake")
    xml_path = _write_musicxml(tmp_path / "page000.musicxml")
    monkeypatch.setattr(
        "punchbox_gui.omr.omr_worker.rasterize_pdf", lambda pdf_path, dpi=300: page_paths
    )

    loop = QEventLoop()
    results = {}

    def on_scores(scores):
        results["scores"] = scores
        loop.quit()

    def on_failed(message):
        results["error"] = message
        loop.quit()

    thread, worker = run_omr_in_background(
        "fake.pdf",
        on_progress=lambda *a: None,
        on_scores=on_scores,
        on_failed=on_failed,
        engine=FakeEngine([xml_path]),
    )

    QTimer.singleShot(5000, loop.quit)  # safety net so a bug can't hang the suite
    loop.exec()
    thread.wait(1000)

    assert "error" not in results
    assert len(results.get("scores", [])) == 1
