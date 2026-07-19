from PySide6.QtCore import QLineF
from PySide6.QtCore import QPointF
from PySide6.QtCore import QSizeF
from PySide6.QtGui import QColor
from PySide6.QtGui import QFont
from PySide6.QtGui import QPageSize
from PySide6.QtGui import QPainter
from PySide6.QtGui import QPen
from PySide6.QtPrintSupport import QPrintDialog
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtPrintSupport import QPrintPreviewDialog

from punchbox.layout import draw_layout

from .qt_painter_renderer import PT_PER_MM
from .qt_painter_renderer import QPainterRenderer


def _mm_font(mm_height, dots_per_mm):
    """A QFont sized so it renders `mm_height` millimeters tall under a painter
    already scaled by `dots_per_mm` - see QPainterRenderer.text() for why the
    naive `mm_height` in points would render dots_per_mm times too large.
    """
    font = QFont()
    font.setPointSizeF(max(mm_height * PT_PER_MM / dots_per_mm, 0.1))
    return font


def _configure_printer(printer, params):
    printer.setPageSize(
        QPageSize(QSizeF(params.page_width, params.page_height), QPageSize.Millimeter)
    )
    printer.setFullPage(True)
    printer.setResolution(300)


def render_to_printer(printer, tune, music_box, params, transpose, name=None):
    """Paint the layout directly onto an already-configured QPrinter/QPaintDevice.

    Public (not print_tune's private detail) so it can be exercised in tests by
    pointing a QPrinter at a PDF file, without needing a real print dialog.
    """
    painter = QPainter(printer)
    dots_per_mm = printer.resolution() / 25.4
    painter.scale(dots_per_mm, dots_per_mm)
    renderer = QPainterRenderer(painter, dots_per_mm, on_new_page=printer.newPage)
    diagnostics = draw_layout(tune, music_box, params, transpose, renderer, name=name)
    painter.end()
    return diagnostics


def print_tune(parent_widget, tune, music_box, params, transpose, name=None):
    """Show the OS print dialog (so the user picks their printer, e.g. the
    ET-2862) and print at exact physical scale - no 'fit to page' is applied on
    our side; setFullPage(True) keeps our own margin authoritative.
    """
    printer = QPrinter(QPrinter.HighResolution)
    _configure_printer(printer, params)
    dialog = QPrintDialog(printer, parent_widget)
    if dialog.exec() != QPrintDialog.Accepted:
        return None
    return render_to_printer(printer, tune, music_box, params, transpose, name=name)


def preview_tune(parent_widget, tune, music_box, params, transpose, name=None):
    printer = QPrinter(QPrinter.HighResolution)
    _configure_printer(printer, params)
    dialog = QPrintPreviewDialog(printer, parent_widget)
    dialog.paintRequested.connect(
        lambda p: render_to_printer(p, tune, music_box, params, transpose, name=name)
    )
    dialog.exec()


def print_calibration_ruler(parent_widget):
    """One-click diagnostic page: a 100mm reference line with 10mm ticks.

    The ET-2862 (or any printer)'s own Windows driver dialog can silently apply
    its own scaling/fit-to-page default independent of anything this app does -
    print this once on real paper and measure it with a ruler before trusting
    any punch-strip printout to be physically accurate.
    """
    printer = QPrinter(QPrinter.HighResolution)
    printer.setPageSize(QPageSize(QPageSize.A4))
    printer.setFullPage(True)
    dialog = QPrintDialog(printer, parent_widget)
    if dialog.exec() != QPrintDialog.Accepted:
        return
    render_calibration_ruler(printer)


def render_calibration_ruler(printer):
    painter = QPainter(printer)
    dots_per_mm = printer.resolution() / 25.4
    painter.scale(dots_per_mm, dots_per_mm)

    pen = QPen(QColor("black"))
    pen.setWidthF(0.2)
    painter.setPen(pen)

    # A QPainter's default font, once run through the mm-scaled transform above,
    # renders many times larger than the page - always set an explicit
    # dots_per_mm-compensated size before drawing text here (see _mm_font).
    # Point-based drawText() is baseline positioned; the rect-based overload
    # silently draws nothing when its rect is smaller than the font's natural
    # line box, so it's avoided throughout.
    painter.setFont(_mm_font(3.0, dots_per_mm))
    painter.drawText(
        QPointF(10.0, 10.0),
        "Calibration: the line below is exactly 100mm. Measure it with a ruler.",
    )

    painter.setFont(_mm_font(2.5, dots_per_mm))

    y = 25.0
    painter.drawLine(QLineF(10.0, y, 110.0, y))
    for mm in range(0, 101, 10):
        tick = 3.0 if mm % 50 else 6.0
        x = 10.0 + mm
        painter.drawLine(QLineF(x, y - tick / 2, x, y + tick / 2))
        painter.drawText(QPointF(x - 2.0, y + 8.0), str(mm))

    painter.end()
