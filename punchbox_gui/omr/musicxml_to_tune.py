import music21

from punchbox.model import NoteEvent
from punchbox.model import Tune


def parse_score(musicxml_path):
    return music21.converter.parse(str(musicxml_path))


def part_names(score):
    """Human-readable names for a picker dialog - jw.org-style piano/vocal
    arrangements commonly have more than one part (e.g. melody + accompaniment
    or full SATB), and guessing which one is the tune to punch would silently
    produce the wrong output, so the caller is expected to ask the user.
    """
    names = []
    for i, part in enumerate(score.parts):
        names.append(part.partName or "Part {}".format(i + 1))
    return names


def score_to_notes(score, part_index=0):
    """Extract NoteEvents (0-based offsets, in quarter-lengths) from one part
    of a parsed Score. Chords explode into one NoteEvent per pitch at the same
    start time rather than collapsing to the top note - the layout/collision
    logic downstream already flags notes the box can't physically play
    together, so this step stays "dumb" and complete.
    """
    parts = list(score.parts)
    if not parts:
        return []
    part = parts[part_index]

    notes = []
    for element in part.flatten().notesAndRests:
        if element.isRest:
            continue
        pitches = element.pitches if element.isChord else [element.pitch]
        lyric = element.lyric
        for pitch in pitches:
            notes.append(
                NoteEvent(
                    pitch=int(pitch.midi),
                    start=float(element.offset),
                    duration=float(element.quarterLength),
                    source="omr",
                    lyric=lyric,
                )
            )
    return notes


def build_tune_from_pages(scores, part_index=0, title="OMR Import"):
    """Combine per-page parsed Scores into one Tune, offsetting each page's
    notes by the running end-time of every page before it.

    OMR recognizes one page image at a time - there's no PDF-wide timeline
    until this stitches the pages together, so merging happens here on our
    own NoteEvent lists rather than by combining music21 Score/Part objects.
    """
    all_notes = []
    running_offset = 0.0

    for score in scores:
        page_notes = score_to_notes(score, part_index=part_index)
        for note in page_notes:
            note.start += running_offset
        all_notes.extend(page_notes)

        parts = list(score.parts)
        page_length = parts[part_index].highestTime if parts else 0.0
        running_offset += page_length

    all_notes.sort(key=lambda n: n.start)

    # OMR is inherently imperfect (true of oemer and even more mature engines
    # alike) - this warning is unconditional, not just for multi-page merges,
    # since the piano-roll's note-correction is a required safety net here,
    # not optional polish, and the diagnostics panel is where the user sees it.
    warnings = ["OMR-recognized notes may contain errors - review each note before printing."]
    if len(scores) > 1:
        warnings.append("{} pages merged".format(len(scores)))

    return Tune(title=title, notes=all_notes, warnings=warnings)
