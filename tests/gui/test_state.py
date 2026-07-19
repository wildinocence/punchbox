import pytest

pytest.importorskip("PySide6")

from punchbox.model import NoteEvent  # noqa: E402
from punchbox.model import Tune  # noqa: E402
from punchbox_gui.state import AppState  # noqa: E402

BOXEN_CONFIG = {
    "boxen": {
        "30note": {"note_data": [60, 62, 64], "pitch": 2.0, "reverse": False, "note_collision": 1.0}
    },
    "divisor": 49.5,
    "margin": 20.0,
    "page": {"width": 297.0, "height": 210.0},
}


def test_boxen_names(qapp):
    state = AppState(BOXEN_CONFIG)
    assert state.boxen_names == ["30note"]


def test_set_music_box_emits_signal(qapp):
    state = AppState(BOXEN_CONFIG)
    seen = []
    state.musicBoxChanged.connect(lambda: seen.append(True))

    state.set_music_box("30note")

    assert seen == [True]
    assert state.music_box.note_data == [60, 62, 64]


def test_set_tune_emits_signal(qapp):
    state = AppState(BOXEN_CONFIG)
    seen = []
    state.tuneChanged.connect(lambda: seen.append(True))

    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0.0)])
    state.set_tune(tune)

    assert seen == [True]
    assert state.tune is tune


def test_compute_transpose_without_music_box_is_safe(qapp):
    state = AppState(BOXEN_CONFIG)
    result = state.compute_transpose()
    assert result.shift == 0
    assert result.fit_fraction == 0.0


def test_layout_params_seeded_from_boxen_config(qapp):
    state = AppState(BOXEN_CONFIG)
    assert state.layout_params.mm_per_quarter == 49.5
    assert state.layout_params.page_width == 297.0


def test_add_note_appends_and_emits(qapp):
    state = AppState(BOXEN_CONFIG)
    seen = []
    state.tuneChanged.connect(lambda: seen.append(True))

    state.add_note(pitch=60, start=2.5)

    assert seen == [True]
    assert len(state.tune.notes) == 1
    added = state.tune.notes[0]
    assert (added.pitch, added.start, added.source) == (60, 2.5, "manual")


def test_add_note_clamps_negative_start():
    state = AppState(BOXEN_CONFIG)
    state.add_note(pitch=60, start=-5.0)
    assert state.tune.notes[0].start == 0.0


def test_move_note_updates_matching_note_by_id(qapp):
    state = AppState(BOXEN_CONFIG)
    state.add_note(pitch=60, start=0.0)
    state.add_note(pitch=62, start=1.0)
    target_id = state.tune.notes[0].id

    seen = []
    state.tuneChanged.connect(lambda: seen.append(True))
    state.move_note(target_id, pitch=64, start=3.0)

    assert seen == [True]
    moved = next(n for n in state.tune.notes if n.id == target_id)
    assert (moved.pitch, moved.start) == (64, 3.0)
    # the other note is untouched
    other = next(n for n in state.tune.notes if n.id != target_id)
    assert (other.pitch, other.start) == (62, 1.0)


def test_move_note_unknown_id_is_a_no_op():
    state = AppState(BOXEN_CONFIG)
    state.add_note(pitch=60, start=0.0)
    state.move_note(note_id=999999, pitch=64, start=3.0)
    assert (state.tune.notes[0].pitch, state.tune.notes[0].start) == (60, 0.0)


def test_delete_notes_removes_only_matching_ids(qapp):
    state = AppState(BOXEN_CONFIG)
    state.add_note(pitch=60, start=0.0)
    state.add_note(pitch=62, start=1.0)
    state.add_note(pitch=64, start=2.0)
    keep_id = state.tune.notes[1].id
    delete_ids = [state.tune.notes[0].id, state.tune.notes[2].id]

    seen = []
    state.tuneChanged.connect(lambda: seen.append(True))
    state.delete_notes(delete_ids)

    assert seen == [True]
    assert [n.id for n in state.tune.notes] == [keep_id]
