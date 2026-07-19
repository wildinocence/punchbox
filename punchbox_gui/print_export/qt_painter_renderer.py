from PySide6.QtCore import QLineF
from PySide6.QtCore import QPointF
from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush
from PySide6.QtGui import QColor
from PySide6.QtGui import QFont
from PySide6.QtGui import QPen

from punchbox.renderer import Renderer

PT_PER_MM = 72.0 / 25.4


class QPainterRenderer(Renderer):
    """Draws a layout via a QPainter whose transform must already be scaled so
    that 1 paint unit == 1 millimeter (see print_controller._configure_printer).

    Used both for actual printing (painter targets a QPrinter) and for exact-scale
    on-screen print preview (painter targets a QPrintPreviewDialog page) - same
    renderer, same geometry, so preview and printout can't diverge.
    """

    def __init__(self, painter, dots_per_mm, on_new_page=None):
        self.painter = painter
        self.dots_per_mm = dots_per_mm
        self.on_new_page = on_new_page
        self._first_page = True

    def new_page(self, width, height):
        if not self._first_page and self.on_new_page is not None:
            self.on_new_page()
        self._first_page = False

    def line(self, x1, y1, x2, y2):
        pen = QPen(QColor("black"))
        pen.setWidthF(0.1)
        self.painter.setPen(pen)
        self.painter.drawLine(QLineF(x1, y1, x2, y2))

    def circle(self, x, y, radius, color):
        self.painter.setPen(QPen(QColor(color)))
        self.painter.setBrush(QBrush(QColor(color)))
        self.painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2, radius * 2))

    def text(self, content, x, y, color, font_size):
        # Baseline-positioned, matching the (x, y) convention svgwrite's text `insert`
        # uses - the rect-based drawText() overload silently draws nothing when the
        # rect is smaller than the font's natural line box, so avoid it here.
        #
        # QFont point size is a physical unit (1/72in) that then gets *further*
        # multiplied by the painter's world transform (our dots-per-mm scale), so
        # naively setting `font_size` in points would render dots_per_mm times too
        # large. Pre-shrink by the same factor so the CTM scales it back to the
        # intended physical millimeter height.
        point_size = max(font_size * PT_PER_MM / self.dots_per_mm, 0.1)
        font = QFont()
        font.setPointSizeF(point_size)
        self.painter.setFont(font)
        self.painter.setPen(QPen(QColor(color)))
        self.painter.drawText(QPointF(x, y), content)

    def save(self):
        pass
