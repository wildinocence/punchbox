from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtWidgets import QGraphicsView

from punchbox.layout import draw_layout

from .scene_renderer import SceneRenderer

_DEFAULT_ZOOM = 4.0  # 1mm -> 4px baseline; users can zoom further from here


class PianoRollView(QGraphicsView):
    """Read-only preview for Phase 2: shows exactly what draw_layout would put on
    paper. Click-to-edit notes is added in a later phase on top of this same view.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.scale(_DEFAULT_ZOOM, _DEFAULT_ZOOM)

    def display_layout(self, tune, music_box, params, transpose, name=None):
        scene = QGraphicsScene(self)
        renderer = SceneRenderer(scene)
        diagnostics = draw_layout(tune, music_box, params, transpose, renderer, name=name)
        self.setScene(scene)
        return diagnostics
