import math
from dataclasses import dataclass
from dataclasses import field
from typing import List
from typing import Optional

from .notes import note_name


@dataclass
class LayoutParams:
    mm_per_quarter: float  # mm of strip per quarter-length beat (was "divisor", MIDI-ticks-per-mm)
    margin: float
    page_width: float
    page_height: float
    marker_offset: float = 6.0
    marker_offset_top: Optional[float] = None
    marker_offset_bottom: Optional[float] = None
    marker_size: float = 5.0
    font_size: float = 1.0


@dataclass
class Diagnostics:
    min_note_distance_mm: Optional[float] = None
    transpose_fit_fraction: float = 0.0
    warnings: List[str] = field(default_factory=list)


def nearest_lane(music_box, pitch):
    """Return (lane_index, exact) for `pitch` on `music_box`.

    Exact match -> that lane, exact=True. Otherwise scans for the closest available
    pitch at or above `pitch` (snap up) and returns its lane, exact=False. The scan
    order below intentionally re-reverses an already-reversed note_data so it always
    walks pitches in true ascending order regardless of the box's `reverse` display
    flag - reverse only changes lane *display* order, not which pitch is "nearest".
    """
    try:
        return music_box.note_data.index(pitch), True
    except ValueError:
        pass

    scan_order = music_box.note_data[::-1] if music_box.reverse else music_box.note_data
    chosen = scan_order[0]
    for candidate in scan_order:
        chosen = candidate
        if pitch > candidate:
            continue
        break
    return music_box.note_data.index(chosen), False


def _cross(renderer, size, lane, time):
    half = size / 2.0
    renderer.line(time - half, lane, time + half, lane)
    renderer.line(time, lane - half, time, lane + half)


def _min_note_distance_mm(notes, mm_per_quarter):
    last_seen = {}
    min_gap = None
    for note in notes:
        prev = last_seen.get(note.pitch)
        if prev is not None:
            gap = (note.start - prev) * mm_per_quarter
            if min_gap is None or gap < min_gap:
                min_gap = gap
        last_seen[note.pitch] = note.start
    return min_gap


def draw_layout(tune, music_box, params, transpose, renderer, name=None):
    """Lay out `tune` for `music_box` and issue the draw calls to `renderer`.

    This is the single geometry implementation shared by SVG export, print output,
    and the GUI's live piano-roll preview - whichever Renderer is passed in, the
    same math produces pixel-identical positions.
    """
    name = name or tune.title
    mark_top = (
        params.marker_offset_top if params.marker_offset_top is not None else params.marker_offset
    )
    mark_btm = (
        params.marker_offset_bottom
        if params.marker_offset_bottom is not None
        else params.marker_offset
    )

    notes = tune.sorted_notes()
    warnings = list(tune.warnings)

    min_note_distance = _min_note_distance_mm(notes, params.mm_per_quarter)
    if min_note_distance is not None and min_note_distance < music_box.note_collision:
        warnings.append(
            "SOME NOTES MAY NOT PLAY: {:.2f}mm note distance is less than {:.2f}mm required".format(
                min_note_distance, music_box.note_collision
            )
        )

    max_time_qlen = max((n.start for n in notes), default=0.0)
    max_length = max_time_qlen * params.mm_per_quarter

    stave_width = (len(music_box.note_data) - 1) * music_box.pitch + params.margin
    staves_per_page = int(math.floor((params.page_height - params.margin) / stave_width))
    max_stave_length = params.page_width - (params.margin * 2)
    no_staves_required = int(math.ceil(max_length / max_stave_length))
    pages = int(math.ceil(no_staves_required / staves_per_page))

    offset = 0
    for page in range(pages):
        renderer.new_page(params.page_width, params.page_height)
        for stave in range(staves_per_page):
            stave_index = (page * staves_per_page) + stave
            offset_time = stave_index * max_stave_length
            line_offset = (stave * stave_width) + params.margin

            _cross(
                renderer,
                params.marker_size,
                line_offset - mark_top,
                params.margin + max_stave_length,
            )
            _cross(
                renderer,
                params.marker_size,
                line_offset + stave_width - params.margin + mark_btm,
                params.margin + max_stave_length,
            )
            _cross(renderer, params.marker_size, line_offset - mark_top, params.margin)
            _cross(
                renderer,
                params.marker_size,
                line_offset + stave_width - params.margin + mark_btm,
                params.margin,
            )

            renderer.text(
                "STAVE {} - {}".format(stave_index, name),
                params.margin * 2,
                line_offset + stave_width - params.margin + params.marker_offset,
                "blue",
                params.font_size,
            )

            for i, note_pitch in enumerate(music_box.note_data):
                line_x = (i * music_box.pitch) + line_offset
                renderer.line(params.margin, line_x, max_stave_length + params.margin, line_x)
                renderer.text(
                    note_name(note_pitch),
                    -2 + params.margin,
                    line_x + params.font_size / 2,
                    "red",
                    params.font_size,
                )

            for note in notes[offset:]:
                offset += 1
                lane, exact = nearest_lane(music_box, note.pitch + transpose.shift)
                note_time = (note.start * params.mm_per_quarter) - offset_time
                if note_time > max_stave_length:
                    offset -= 1
                    break
                renderer.circle(
                    note_time + params.margin,
                    (lane * music_box.pitch) + line_offset,
                    1.0,
                    "black" if exact else "red",
                )
        renderer.save()

    if transpose.fit_fraction != 1.0:
        warnings.append("PERFECT TRANSPOSITION NOT FOUND")

    return Diagnostics(
        min_note_distance_mm=min_note_distance,
        transpose_fit_fraction=transpose.fit_fraction,
        warnings=warnings,
    )
