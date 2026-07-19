import pytest

music21 = pytest.importorskip("music21")

from punchbox_gui.omr.musicxml_to_tune import build_tune_from_pages  # noqa: E402
from punchbox_gui.omr.musicxml_to_tune import parse_score  # noqa: E402
from punchbox_gui.omr.musicxml_to_tune import part_names  # noqa: E402
from punchbox_gui.omr.musicxml_to_tune import score_to_notes  # noqa: E402


def _single_part_score(pitches_with_lyrics, part_name="Melody"):
    part = music21.stream.Part()
    part.partName = part_name
    for pitch_name, lyric in pitches_with_lyrics:
        n = music21.note.Note(pitch_name, quarterLength=1.0)
        if lyric is not None:
            n.lyric = lyric
        part.append(n)
    score = music21.stream.Score()
    score.append(part)
    return score


def test_score_to_notes_extracts_pitch_offset_and_lyric():
    score = _single_part_score([("C4", "Hel"), ("D4", "lo"), ("E4", None)])

    notes = score_to_notes(score)

    assert [(n.pitch, n.start, n.lyric) for n in notes] == [
        (60, 0.0, "Hel"),
        (62, 1.0, "lo"),
        (64, 2.0, None),
    ]
    assert all(n.source == "omr" for n in notes)


def test_score_to_notes_explodes_chords_into_one_note_per_pitch():
    part = music21.stream.Part()
    chord = music21.chord.Chord(["C4", "E4", "G4"], quarterLength=1.0)
    part.append(chord)
    score = music21.stream.Score()
    score.append(part)

    notes = score_to_notes(score)

    assert sorted(n.pitch for n in notes) == [60, 64, 67]
    assert all(n.start == 0.0 for n in notes)


def test_score_to_notes_skips_rests():
    part = music21.stream.Part()
    part.append(music21.note.Note("C4", quarterLength=1.0))
    part.append(music21.note.Rest(quarterLength=1.0))
    part.append(music21.note.Note("D4", quarterLength=1.0))
    score = music21.stream.Score()
    score.append(part)

    notes = score_to_notes(score)

    assert [n.pitch for n in notes] == [60, 62]
    assert [n.start for n in notes] == [0.0, 2.0]


def test_part_names_lists_every_part_for_a_required_picker():
    score = music21.stream.Score()
    soprano = music21.stream.Part()
    soprano.partName = "Soprano"
    alto = music21.stream.Part()
    alto.partName = "Alto"
    score.append(soprano)
    score.append(alto)

    assert part_names(score) == ["Soprano", "Alto"]


def test_build_tune_from_pages_offsets_each_page_by_the_previous_pages_length():
    page1 = _single_part_score([("C4", None), ("D4", None)])  # ends at offset 2.0
    page2 = _single_part_score([("E4", None), ("F4", None)])

    tune = build_tune_from_pages([page1, page2], title="Two Pages")

    assert [(n.pitch, n.start) for n in tune.notes] == [
        (60, 0.0),
        (62, 1.0),
        (64, 2.0),
        (65, 3.0),
    ]
    assert "2 pages merged" in tune.warnings


def test_build_tune_from_pages_no_merge_warning_for_a_single_page():
    page = _single_part_score([("C4", None)])
    tune = build_tune_from_pages([page])
    assert not any("pages merged" in w for w in tune.warnings)


def test_build_tune_from_pages_always_warns_to_review_omr_output():
    page = _single_part_score([("C4", None)])
    tune = build_tune_from_pages([page])
    assert any("review" in w.lower() for w in tune.warnings)


def test_build_tune_from_pages_uses_the_selected_part_index():
    score = music21.stream.Score()
    melody = music21.stream.Part()
    melody.partName = "Melody"
    melody.append(music21.note.Note("C5", quarterLength=1.0))
    bass = music21.stream.Part()
    bass.partName = "Bass"
    bass.append(music21.note.Note("C3", quarterLength=1.0))
    score.append(melody)
    score.append(bass)

    tune = build_tune_from_pages([score], part_index=1)

    assert [n.pitch for n in tune.notes] == [48]  # C3


def test_parse_score_round_trips_a_real_musicxml_file(tmp_path):
    # This is what oemer actually hands us: a .musicxml file on disk, not an
    # in-memory Score - exercise parse_score()'s real converter.parse() call,
    # not just direct in-memory Score construction like the tests above.
    original = _single_part_score([("C4", "A"), ("E4", "men")])
    xml_path = tmp_path / "page000.musicxml"
    original.write("musicxml", fp=str(xml_path))

    parsed = parse_score(xml_path)
    notes = score_to_notes(parsed)

    assert [(n.pitch, n.lyric) for n in notes] == [(60, "A"), (64, "men")]
