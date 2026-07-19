from mido import MidiFile

from .model import NoteEvent
from .model import Tune


def load_tune_from_midi(filename, tracks=None, title=None):
    """Load a Tune from a MIDI file. note_on events with velocity 0 (== note_off) are skipped.

    `tracks` restricts which track indices are read (default: all of the first 16).
    """
    if tracks is None:
        tracks = range(16)

    notes = []
    with MidiFile(filename) as midi_file:
        ticks_per_beat = midi_file.ticks_per_beat
        for i, track in enumerate(midi_file.tracks):
            if i not in tracks:
                continue
            time = 0
            for message in track:
                time += message.time
                if message.type == "note_on" and message.velocity > 0:
                    notes.append(
                        NoteEvent(pitch=message.note, start=time / ticks_per_beat, source="midi")
                    )

    notes.sort(key=lambda n: n.start)
    return Tune(title=title or filename, notes=notes, source_path=filename)
