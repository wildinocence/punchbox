from PySide6.QtCore import QLineF
from PySide6.QtGui import QBrush
from PySide6.QtGui import QColor
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QGraphicsSimpleTextItem

from punchbox.renderer import Renderer

from .note_item import NoteItem

_MM_TO_PT = 2.83  # rough conversion for on-screen legibility only, not print accuracy
_PAGE_GAP_MM = 10.0


class SceneRenderer(Renderer):
    """Renders a layout into a QGraphicsScene, one scene unit == one millimeter -
    the same coordinate space compute/draw_layout produces, so what's on screen
    is a literal (if tiny at 1x zoom) preview of the physical strip.

    Pages are stacked vertically with a gap rather than paginated, since the live
    preview is a continuous scroll, not a print layout. `page_offsets[i]` records
    each page's cumulative y offset, so callers (PianoRollView) can map a scene
    click back to a (page, local position) for editing.
    """

    def __init__(self, scene, on_note_released=None):
        self.scene = scene
        self.page_offsets = []
        self._on_note_released = on_note_released
        self._y_offset = 0.0
        self._page_height = 0.0
        self._first_page = True

    def new_page(self, width, height):
        if not self._first_page:
            self._y_offset += self._page_height + _PAGE_GAP_MM
        self._first_page = False
        self._page_height = height
        self.page_offsets.append(self._y_offset)
        self.scene.addRect(0, self._y_offset, width, height, QPen(QColor("lightGray")))

    def line(self, x1, y1, x2, y2):
        pen = QPen(QColor("black"))
        pen.setWidthF(0.1)
        self.scene.addLine(QLineF(x1, y1 + self._y_offset, x2, y2 + self._y_offset), pen)

    def circle(self, x, y, radius, color, note_id=None):
        item = NoteItem(
            note_id, x, y + self._y_offset, radius, color, on_released=self._on_note_released
        )
        self.scene.addItem(item)

    def text(self, content, x, y, color, font_size):
        item = QGraphicsSimpleTextItem(content)
        item.setBrush(QBrush(QColor(color)))
        font = item.font()
        font.setPointSizeF(max(font_size * _MM_TO_PT, 1.0))
        item.setFont(font)
        item.setPos(x, y + self._y_offset - font_size)
        self.scene.addItem(item)

    def save(self):
        pass
