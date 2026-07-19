from PySide6.QtCore import QObject
from PySide6.QtCore import Signal

from punchbox.config import MusicBox
from punchbox.layout import LayoutParams
from punchbox.model import NoteEvent
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
        # None = auto-search on every compute_transpose() call (right for a freshly
        # loaded MIDI/OMR tune, where finding the best-fitting shift is the point).
        # Once the user manually places a note, the shift in effect at that moment
        # gets locked here - otherwise adding a second note could change the best
        # overall fit and silently teleport the first note to a different lane.
        self._transpose_override = None

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
        self._transpose_override = None  # a freshly loaded tune re-enables auto-search
        self.tuneChanged.emit()

    def set_music_box(self, name):
        self._music_box_name = name
        self._music_box = MusicBox(self._boxen_config["boxen"][name])
        self.musicBoxChanged.emit()

    def set_layout_params(self, **overrides):
        for key, value in overrides.items():
            setattr(self._layout_params, key, value)
        self.layoutParamsChanged.emit()

    def add_note(self, pitch, start, duration=0.25, source="manual"):
        self._lock_transpose()
        self._tune.notes.append(
            NoteEvent(pitch=pitch, start=max(start, 0.0), duration=duration, source=source)
        )
        self.tuneChanged.emit()

    def move_note(self, note_id, pitch, start):
        self._lock_transpose()
        for note in self._tune.notes:
            if note.id == note_id:
                note.pitch = pitch
                note.start = max(start, 0.0)
                break
        self.tuneChanged.emit()

    def delete_notes(self, note_ids):
        ids = set(note_ids)
        self._tune.notes = [note for note in self._tune.notes if note.id not in ids]
        self.tuneChanged.emit()

    def _lock_transpose(self):
        if self._transpose_override is None:
            self._transpose_override = self.compute_transpose().shift

    def compute_transpose(self):
        if self._music_box is None:
            return TransposeResult(shift=0, fit_fraction=0.0)
        if self._transpose_override is not None:
            # Fit at a single fixed shift - reuses find_best_transpose's own
            # fit/missing-note computation by searching a range of exactly one.
            shift = self._transpose_override
            return find_best_transpose(self._tune, self._music_box.note_data, shift, shift + 1)
        return find_best_transpose(
            self._tune, self._music_box.note_data, self._transpose_lower, self._transpose_upper
        )
