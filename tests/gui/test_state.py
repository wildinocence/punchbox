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
