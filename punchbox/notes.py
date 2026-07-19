NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(value):
    """Convert a MIDI note number to a name like 'C#4'."""
    name = NOTE_NAMES[value % 12]
    octave = (value // 12) - 2
    return "{}{}".format(name, octave)
