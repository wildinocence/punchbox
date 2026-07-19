from punchbox.model import NoteEvent
from punchbox.model import Tune
from punchbox.transpose import find_best_transpose


def _tune(pitches):
    return Tune(title="t", notes=[NoteEvent(pitch=p, start=i) for i, p in enumerate(pitches)])


def test_perfect_fit_at_zero_shift():
    note_data = [60, 62, 64]
    result = find_best_transpose(_tune([60, 62, 64]), note_data, -5, 5)
    assert result.shift == 0
    assert result.fit_fraction == 1.0
    assert result.missing == {}


def test_finds_shift_that_fits():
    note_data = [60, 62, 64]
    # A whole tone up from note_data: fits perfectly at shift=-2.
    result = find_best_transpose(_tune([62, 64, 66]), note_data, -5, 5)
    assert result.shift == -2
    assert result.fit_fraction == 1.0


def test_partial_fit_reports_missing_notes_by_name():
    note_data = [60, 62, 64]
    result = find_best_transpose(_tune([60, 62, 99]), note_data, 0, 1)
    assert result.shift == 0
    assert result.fit_fraction == 2 / 3
    assert result.missing == {"D#6": 1}


def test_last_perfect_match_wins_tie_break():
    # A single note that fits both at shift=0 (as-is) and shift=12 (an octave up);
    # the loop overwrites the best result on every perfect match, so the highest
    # shift tried wins - this is the original implementation's tie-break, preserved.
    note_data = [60, 72]
    result = find_best_transpose(_tune([60]), note_data, 0, 13)
    assert result.shift == 12
    assert result.fit_fraction == 1.0


def test_empty_tune_returns_zero_shift_without_error():
    result = find_best_transpose(_tune([]), [60, 62, 64], -5, 5)
    assert result.shift == 0
    assert result.fit_fraction == 0.0
