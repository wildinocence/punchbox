from PySide6.QtCore import QObject
from PySide6.QtCore import Signal

from punchbox.config import MusicBox
from punchbox.layout import LayoutParams
from punchbox.model import Tune
from punchbox.transpose import find_best_transpose
from punchbox.transpose import TransposeResult


class AppState(QObject):
    """Single shared source of truth for the open tune, music box, and layout
    settings. The piano-roll view, audio engine (later phase), and print/export
    panel all read from here rather than keeping their own copies, so an edit in
    one place is immediately reflected everywhere else.
    """

    tuneChanged = Signal()
    musicBoxChanged = Signal()
    layoutParamsChanged = Signal()

    def __init__(self, boxen_config, parent=None):
        super().__init__(parent)
        self._boxen_config = boxen_config
        self._tune = Tune(title="Untitled", notes=[])
        self._music_box_name = None
        self._music_box = None
        self._layout_params = LayoutParams(
            mm_per_quarter=boxen_config.get("divisor", 49.5),
            margin=boxen_config.get("margin", 20.0),
            page_width=boxen_config.get("page", {}).get("width", 297.0),
            page_height=boxen_config.get("page", {}).get("height", 210.0),
            marker_offset=boxen_config.get("marker_offset", 6.0),
            marker_size=boxen_config.get("marker_size", 5.0),
            font_size=boxen_config.get("font_size", 1.0),
        )
        self._transpose_lower = boxen_config.get("transpose", {}).get("lower", -100)
        self._transpose_upper = boxen_config.get("transpose", {}).get("upper", 100)

    @property
    def tune(self):
        return self._tune

    @property
    def music_box(self):
        return self._music_box

    @property
    def layout_params(self):
        return self._layout_params

    @property
    def boxen_names(self):
        return sorted(self._boxen_config.get("boxen", {}).keys())

    def set_tune(self, tune):
        self._tune = tune
        self.tuneChanged.emit()

    def set_music_box(self, name):
        self._music_box_name = name
        self._music_box = MusicBox(self._boxen_config["boxen"][name])
        self.musicBoxChanged.emit()

    def set_layout_params(self, **overrides):
        for key, value in overrides.items():
            setattr(self._layout_params, key, value)
        self.layoutParamsChanged.emit()

    def compute_transpose(self):
        if self._music_box is None:
            return TransposeResult(shift=0, fit_fraction=0.0)
        return find_best_transpose(
            self._tune, self._music_box.note_data, self._transpose_lower, self._transpose_upper
        )
