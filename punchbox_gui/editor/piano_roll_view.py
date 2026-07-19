from PySide6.QtCore import Qt
from PySide6.QtCore import Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtWidgets import QGraphicsView

from punchbox.layout import compute_stave_geometry
from punchbox.layout import draw_layout
from punchbox.layout import scene_point_to_note

from .note_item import NoteItem
from .scene_renderer import SceneRenderer

_DEFAULT_ZOOM = 4.0  # 1mm -> 4px baseline; users can zoom further from here


class PianoRollView(QGraphicsView):
    """Shows exactly what draw_layout would put on paper - X/Y are the same
    millimeter coordinates as SVG/print output - and lets the user compose
    directly on it: click an empty lane to add a note, drag a note to move it
    (snapping to the nearest lane and to the click position in time), select
    and press Delete to remove notes.

    This view never mutates AppState itself - it only emits requests; the
    owner (MainWindow) wires them to AppState so the view stays testable and
    reusable without a real app around it.
    """

    noteAddRequested = Signal(int, float)  # pitch, start (quarter-lengths)
    noteMoveRequested = Signal(int, int, float)  # note_id, pitch, start
    notesDeleteRequested = Signal(list)  # list[int] note_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.scale(_DEFAULT_ZOOM, _DEFAULT_ZOOM)

        self._music_box = None
        self._params = None
        self._transpose = None
        self._geometry = None
        self._page_offsets = []

    def display_layout(self, tune, music_box, params, transpose, name=None):
        scene = QGraphicsScene(self)
        renderer = SceneRenderer(scene, on_note_released=self._handle_note_released)
        diagnostics = draw_layout(tune, music_box, params, transpose, renderer, name=name)
        self.setScene(scene)

        self._music_box = music_box
        self._params = params
        self._transpose = transpose
        self._geometry = compute_stave_geometry(tune, music_box, params)
        self._page_offsets = renderer.page_offsets
        return diagnostics

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            item = self.itemAt(pos)
            if not isinstance(item, NoteItem):
                result = self._point_to_note(self.mapToScene(pos))
                if result is not None:
                    pitch, start = result
                    self.noteAddRequested.emit(pitch, start)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            ids = [
                item.note_id for item in self.scene().selectedItems() if isinstance(item, NoteItem)
            ]
            if ids:
                self.notesDeleteRequested.emit(ids)
                return
        super().keyPressEvent(event)

    def _handle_note_released(self, item):
        result = self._point_to_note(item.scenePos())
        if result is not None:
            pitch, start = result
            self.noteMoveRequested.emit(item.note_id, pitch, start)

    def _point_to_note(self, scene_pos):
        if self._music_box is None or self._geometry is None or not self._page_offsets:
            return None

        page_index = None
        for i, offset in enumerate(self._page_offsets):
            if offset <= scene_pos.y() <= offset + self._params.page_height:
                page_index = i
                break
        if page_index is None:
            return None

        y_in_page = scene_pos.y() - self._page_offsets[page_index]
        result = scene_point_to_note(
            page_index, scene_pos.x(), y_in_page, self._music_box, self._params, self._geometry
        )
        if result is None:
            return None

        lane_pitch, start_qlen = result
        return lane_pitch - self._transpose.shift, start_qlen
