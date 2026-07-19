import mido

from punchbox.midi_source import load_tune_from_midi


def _write_midi(path, ticks_per_beat=480):
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)

    track0 = mido.MidiTrack()
    mid.tracks.append(track0)
    track0.append(mido.Message("note_on", note=60, velocity=64, time=0))
    track0.append(mido.Message("note_on", note=62, velocity=64, time=ticks_per_beat))
    # velocity=0 note_on is a note-off in disguise and must be skipped, not treated as a note.
    track0.append(mido.Message("note_on", note=64, velocity=0, time=0))

    track1 = mido.MidiTrack()
    mid.tracks.append(track1)
    track1.append(mido.Message("note_on", note=48, velocity=64, time=0))

    mid.save(str(path))


def test_load_tune_from_midi_converts_ticks_to_quarter_lengths(tmp_path):
    path = tmp_path / "test.mid"
    _write_midi(path)

    tune = load_tune_from_midi(str(path))

    assert [(n.pitch, n.start) for n in tune.sorted_notes()] == [
        (60, 0.0),
        (48, 0.0),
        (62, 1.0),
    ]
    assert all(n.source == "midi" for n in tune.notes)


def test_velocity_zero_note_on_is_treated_as_note_off(tmp_path):
    path = tmp_path / "test.mid"
    _write_midi(path)

    tune = load_tune_from_midi(str(path))

    assert 64 not in [n.pitch for n in tune.notes]


def test_track_filtering(tmp_path):
    path = tmp_path / "test.mid"
    _write_midi(path)

    tune = load_tune_from_midi(str(path), tracks=[0])

    assert 48 not in [n.pitch for n in tune.notes]
    assert {60, 62} == {n.pitch for n in tune.notes}
