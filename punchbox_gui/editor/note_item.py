from PySide6.QtGui import QBrush
from PySide6.QtGui import QColor
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QGraphicsEllipseItem


class NoteItem(QGraphicsEllipseItem):
    """A draggable, selectable dot representing one NoteEvent in the piano-roll
    editor. The local rect is centered at the origin and the item is placed via
    setPos(), so scenePos() after a drag directly gives the note's new (x, y) in
    the same millimeter coordinate space draw_layout uses.
    """

    def __init__(self, note_id, x, y, radius, color, on_released=None):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.note_id = note_id
        self._on_released = on_released
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor(color)))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setZValue(1.0)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._on_released is not None:
            self._on_released(self)
