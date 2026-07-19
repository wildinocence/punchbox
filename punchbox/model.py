import itertools
from dataclasses import dataclass
from dataclasses import field
from typing import List
from typing import Optional

_id_counter = itertools.count(1)


def _next_note_id():
    return next(_id_counter)


@dataclass
class NoteEvent:
    """A single note, independent of where it came from (MIDI, OMR, manual edit)."""

    pitch: int
    start: float  # quarter-lengths (beats) from the start of the tune
    duration: float = 0.25  # quarter-lengths; informational, not used for punch-strip layout
    source: str = "unknown"  # "midi" | "omr" | "manual"
    lyric: Optional[str] = None  # syllable for this note, populated by OMR
    id: int = field(default_factory=_next_note_id)


@dataclass
class Tune:
    """A source-agnostic tune: a bag of NoteEvents plus provenance/warnings."""

    title: str
    notes: List[NoteEvent]
    source_path: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def sorted_notes(self):
        return sorted(self.notes, key=lambda n: n.start)
