from punchbox.notes import note_name


def test_note_name_basic():
    assert note_name(60) == "C3"


def test_note_name_sharp():
    # Regression test: under Python 2 `(val / 12) - 2` used integer division and
    # happened to work; under Python 3 `/` is float division and this silently
    # produced names like "C#3.0833333333333335" unless `//` is used.
    assert note_name(61) == "C#3"


def test_note_name_octave_boundary():
    assert note_name(72) == "C4"
    assert note_name(59) == "B2"
