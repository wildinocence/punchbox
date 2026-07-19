from PySide6.QtCore import QObject
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal

from .musicxml_to_tune import parse_score
from .oemer_engine import OemerEngine
from .pdf_raster import rasterize_pdf


class OmrWorker(QObject):
    """Runs PDF -> rasterize -> OMR -> parsed Score on a background thread.

    Rasterizing pages and shelling out to an OMR engine per page can take real
    wall-clock time (seconds to low minutes for a multi-page PDF) and must
    never block the Qt event loop. Emits parsed music21 Scores rather than a
    finished Tune, because turning scores into a Tune may need a part-picker
    dialog first when a score has more than one part - that has to happen on
    the main thread, not here.
    """

    progress = Signal(int, int, str)  # current, total, message
    scoresReady = Signal(list)  # list[music21 Score], one per page
    failed = Signal(str)

    def __init__(self, pdf_path, engine=None, dpi=300):
        super().__init__()
        self.pdf_path = pdf_path
        self.engine = engine or OemerEngine()
        self.dpi = dpi
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            pages = rasterize_pdf(self.pdf_path, dpi=self.dpi)
            total = len(pages)
            scores = []
            for i, page_path in enumerate(pages):
                if self._cancelled:
                    return
                self.progress.emit(
                    i, total, "Recognizing page {} of {}...".format(i + 1, total)
                )
                musicxml_path = self.engine.recognize_page(page_path, page_path.parent)
                if self._cancelled:
                    return
                scores.append(parse_score(musicxml_path))
            if self._cancelled:
                return
            self.progress.emit(total, total, "Done")
            self.scoresReady.emit(scores)
        except Exception as exc:
            self.failed.emit(str(exc))


def run_omr_in_background(pdf_path, on_progress, on_scores, on_failed, engine=None, dpi=300):
    """Starts an OmrWorker on its own QThread and wires its signals to the
    given callbacks (invoked on the caller's/main thread via Qt's queued
    connections). Returns (thread, worker) - the caller must keep both alive
    (e.g. as attributes) until the work finishes, or Qt may garbage-collect
    them mid-run.
    """
    thread = QThread()
    worker = OmrWorker(pdf_path, engine=engine, dpi=dpi)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.progress.connect(on_progress)
    worker.scoresReady.connect(on_scores)
    worker.failed.connect(on_failed)
    worker.scoresReady.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker
