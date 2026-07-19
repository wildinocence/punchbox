from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from typing import Dict

from .notes import note_name


@dataclass
class TransposeResult:
    shift: int
    fit_fraction: float
    missing: Dict[str, int] = field(default_factory=dict)  # note name -> unavailable count


def find_best_transpose(tune, note_data, lower, upper):
    """Search semitone shifts in [lower, upper) for the one that lets the most notes
    in `tune` land on a pitch present in `note_data`.

    Note: when multiple shifts achieve a 100% fit, the *last* one checked wins, not the
    first - this mirrors the original implementation's tie-break and is preserved
    deliberately, since it changes which pitches end up used for a real box.
    """
    notes_use = defaultdict(int)
    for note in tune.notes:
        notes_use[note.pitch] += 1
    total = len(tune.notes)

    best = TransposeResult(shift=0, fit_fraction=0.0, missing={})
    if total == 0:
        return best

    note_data_set = set(note_data)
    for shift in range(lower, upper):
        avail = sum(freq for pitch, freq in notes_use.items() if pitch + shift in note_data_set)
        fraction = avail / total
        if fraction == 1.0:
            best = TransposeResult(shift=shift, fit_fraction=1.0, missing={})
        elif fraction > best.fit_fraction:
            missing = {
                note_name(pitch): freq
                for pitch, freq in notes_use.items()
                if pitch + shift not in note_data_set
            }
            best = TransposeResult(shift=shift, fit_fraction=fraction, missing=missing)
    return best
