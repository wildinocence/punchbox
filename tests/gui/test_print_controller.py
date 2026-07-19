import pytest

pytest.importorskip("PySide6")
fitz = pytest.importorskip("fitz")  # PyMuPDF, used to verify text actually rendered

from PySide6.QtCore import QSizeF  # noqa: E402
from PySide6.QtGui import QPageSize  # noqa: E402
from PySide6.QtPrintSupport import QPrinter  # noqa: E402

from punchbox.config import MusicBox  # noqa: E402
from punchbox.layout import LayoutParams  # noqa: E402
from punchbox.model import NoteEvent  # noqa: E402
from punchbox.model import Tune  # noqa: E402
from punchbox.transpose import TransposeResult  # noqa: E402
from punchbox_gui.print_export import print_controller  # noqa: E402


def _pdf_printer(tmp_path, width_mm, height_mm):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(tmp_path / "out.pdf"))
    printer.setPageSize(QPageSize(QSizeF(width_mm, height_mm), QPageSize.Millimeter))
    printer.setFullPage(True)
    printer.setResolution(150)
    return printer


def test_render_to_printer_produces_a_pdf(tmp_path, qapp):
    box = MusicBox({"note_data": [60, 62, 64], "pitch": 2.0, "note_collision": 1.0})
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0), NoteEvent(pitch=62, start=1)])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    transpose = TransposeResult(shift=0, fit_fraction=1.0)

    # Physical page is (page_height, page_width) - see render_to_printer's rotation.
    printer = _pdf_printer(tmp_path, params.page_height, params.page_width)
    diagnostics = print_controller.render_to_printer(
        printer, tune, box, params, transpose, name="t"
    )

    out_file = tmp_path / "out.pdf"
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert diagnostics.transpose_fit_fraction == 1.0

    # Regression check: the rect-based QPainter.drawText() overload silently
    # draws nothing when its rect is smaller than the font's natural line box -
    # confirm note-name/stave-title text actually made it into the PDF content,
    # not just that lines/dots did.
    doc = fitz.open(str(out_file))
    text = doc[0].get_text()
    assert "STAVE 0" in text
    assert "C3" in text  # note_name(60)


def test_render_to_printer_handles_multiple_pages(tmp_path, qapp):
    box = MusicBox({"note_data": [60, 62], "pitch": 2.0, "note_collision": 1.0})
    notes = [NoteEvent(pitch=60 if i % 2 == 0 else 62, start=i) for i in range(20)]
    tune = Tune(title="t", notes=notes)
    params = LayoutParams(mm_per_quarter=10.0, margin=2.0, page_width=30.0, page_height=10.0)
    transpose = TransposeResult(shift=0, fit_fraction=1.0)

    printer = _pdf_printer(tmp_path, params.page_height, params.page_width)
    # Should not raise despite requiring printer.newPage() to be called internally.
    print_controller.render_to_printer(printer, tune, box, params, transpose, name="t")

    assert (tmp_path / "out.pdf").stat().st_size > 0


def test_render_to_printer_rotates_to_match_a_narrow_long_strip(tmp_path, qapp):
    # Mirrors the real 30-note box's shape (narrow across notes, long along
    # time) at a small scale: a 20mm-wide, 60mm-long physical strip.
    box = MusicBox({"note_data": [60, 62, 64], "pitch": 2.0, "note_collision": 1.0})
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0)])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=60.0, page_height=20.0)
    transpose = TransposeResult(shift=0, fit_fraction=1.0)

    printer = _pdf_printer(tmp_path, params.page_height, params.page_width)
    print_controller.render_to_printer(printer, tune, box, params, transpose, name="t")

    page = fitz.open(str(tmp_path / "out.pdf"))[0]
    pt_per_mm = 2.8346
    assert page.rect.width == pytest.approx(params.page_height * pt_per_mm, abs=1.0)
    assert page.rect.height == pytest.approx(params.page_width * pt_per_mm, abs=1.0)


def test_render_calibration_ruler_produces_a_pdf(tmp_path, qapp):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(tmp_path / "ruler.pdf"))
    printer.setPageSize(QPageSize(QPageSize.A4))
    printer.setFullPage(True)
    printer.setResolution(150)

    print_controller.render_calibration_ruler(printer)

    out_file = tmp_path / "ruler.pdf"
    assert out_file.exists()
    assert out_file.stat().st_size > 0

    text = fitz.open(str(out_file))[0].get_text()
    assert "Calibration" in text
    assert "100" in text
