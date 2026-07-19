import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from punchbox_gui.editor.note_item import NoteItem  # noqa: E402
from punchbox_gui.editor.piano_roll_view import PianoRollView  # noqa: E402
from punchbox_gui.state import AppState  # noqa: E402

BOXEN_CONFIG = {
    "boxen": {
        "30note": {"note_data": [60, 62, 64], "pitch": 2.0, "reverse": False, "note_collision": 1.0}
    },
    "divisor": 10.0,
    "margin": 5.0,
    "page": {"width": 50.0, "height": 50.0},
}


def _wire(state, view):
    """Mirrors MainWindow's wiring: view requests -> state mutations -> re-render."""

    def refresh():
        view.display_layout(
            state.tune, state.music_box, state.layout_params, state.compute_transpose()
        )

    state.tuneChanged.connect(refresh)
    view.noteAddRequested.connect(state.add_note)
    view.noteMoveRequested.connect(state.move_note)
    view.notesDeleteRequested.connect(state.delete_notes)
    refresh()


def _note_items(view):
    return [item for item in view.scene().items() if isinstance(item, NoteItem)]


def test_clicking_an_empty_lane_adds_a_note(qapp):
    state = AppState(BOXEN_CONFIG)
    state.set_music_box("30note")
    view = PianoRollView()
    _wire(state, view)
    assert state.tune.notes == []

    # Lane 0 (pitch 60) at time 0 is scene position (margin, margin) = (5, 5).
    viewport_pos = view.mapFromScene(QPointF(5.0, 5.0))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=viewport_pos)

    assert len(state.tune.notes) == 1
    added = state.tune.notes[0]
    assert (added.pitch, added.start, added.source) == (60, 0.0, "manual")
    assert len(_note_items(view)) == 1


def test_clicking_an_existing_note_does_not_add_another(qapp):
    state = AppState(BOXEN_CONFIG)
    state.set_music_box("30note")
    view = PianoRollView()
    _wire(state, view)

    state.add_note(pitch=60, start=0.0)
    viewport_pos = view.mapFromScene(QPointF(5.0, 5.0))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=viewport_pos)

    assert len(state.tune.notes) == 1


def test_dragging_a_note_moves_it_in_state(qapp):
    state = AppState(BOXEN_CONFIG)
    state.set_music_box("30note")
    view = PianoRollView()
    _wire(state, view)

    state.add_note(pitch=60, start=0.0)  # lane 0, scene (5, 5)
    note_id = state.tune.notes[0].id

    start_pos = view.mapFromScene(QPointF(5.0, 5.0))
    end_pos = view.mapFromScene(QPointF(15.0, 7.0))  # lane 1 (pitch 62), start=1.0

    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start_pos)
    QTest.mouseMove(view.viewport(), pos=end_pos)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end_pos)

    moved = next(n for n in state.tune.notes if n.id == note_id)
    assert (moved.pitch, moved.start) == (62, 1.0)


def test_selecting_and_deleting_a_note_removes_it(qapp):
    state = AppState(BOXEN_CONFIG)
    state.set_music_box("30note")
    view = PianoRollView()
    _wire(state, view)

    state.add_note(pitch=60, start=0.0)
    assert len(state.tune.notes) == 1

    item = _note_items(view)[0]
    item.setSelected(True)
    view.keyPressEvent(_delete_key_event())

    assert state.tune.notes == []


def _delete_key_event():
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent

    return QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)


def test_empty_tune_still_shows_a_clickable_page(qapp):
    state = AppState(BOXEN_CONFIG)
    state.set_music_box("30note")
    view = PianoRollView()
    _wire(state, view)

    # No crash, and the background page rect exists even with zero notes.
    assert view.scene() is not None
    assert len(view.scene().items()) > 0
