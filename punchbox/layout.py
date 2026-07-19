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


@dataclass
class StaveGeometry:
    staves_per_page: int
    stave_width: float
    max_stave_length: float
    pages: int


def compute_stave_geometry(tune, music_box, params):
    """The pure pagination math shared by draw_layout() and the GUI's inverse
    scene-position-to-note mapping (scene_point_to_note) - kept as a single
    implementation so the two can never drift apart.

    A tune with no notes still gets at least one page/stave, so an empty,
    freshly-created tune has somewhere for the piano-roll editor to click.
    """
    max_time_qlen = max((n.start for n in tune.notes), default=0.0)
    max_length = max_time_qlen * params.mm_per_quarter

    stave_width = (len(music_box.note_data) - 1) * music_box.pitch + params.margin
    staves_per_page = int(math.floor((params.page_height - params.margin) / stave_width))
    max_stave_length = params.page_width - (params.margin * 2)
    no_staves_required = int(math.ceil(max_length / max_stave_length))
    pages = max(int(math.ceil(no_staves_required / staves_per_page)), 1)

    return StaveGeometry(
        staves_per_page=staves_per_page,
        stave_width=stave_width,
        max_stave_length=max_stave_length,
        pages=pages,
    )


def scene_point_to_note(page_index, x_in_page, y_in_page, music_box, params, geometry):
    """Invert draw_layout's geometry: given a click at (x_in_page, y_in_page) mm
    within page `page_index`, return (pitch, start_qlen) for the note lane/time
    under that point, or None if the click missed every lane/stave/time range.

    `pitch` is the music box's own note_data value at that lane - the caller is
    responsible for subtracting the current transpose shift to get a raw
    NoteEvent.pitch, mirroring how draw_layout adds it before calling
    nearest_lane() in the forward direction.
    """
    if geometry.staves_per_page <= 0:
        return None

    stave = int((y_in_page - params.margin) // geometry.stave_width)
    if stave < 0 or stave >= geometry.staves_per_page:
        return None

    line_offset = (stave * geometry.stave_width) + params.margin
    lane = round((y_in_page - line_offset) / music_box.pitch)
    if lane < 0 or lane >= len(music_box.note_data):
        return None

    note_time = x_in_page - params.margin
    if note_time < 0 or note_time > geometry.max_stave_length:
        return None

    stave_index = (page_index * geometry.staves_per_page) + stave
    offset_time = stave_index * geometry.max_stave_length
    start_qlen = (note_time + offset_time) / params.mm_per_quarter

    return music_box.note_data[lane], start_qlen


def stave_position_for_time_mm(time_mm, params, geometry):
    """Inverse of the per-stave time offset draw_layout uses internally: given
    an absolute time in mm along the strip, return (page_index, stave,
    x_in_page) - the same page/stave-row/x a note at that time would be drawn
    on. Used to place a playhead in sync with audio playback, which tracks
    time directly rather than any single note's position.
    """
    stave_index = int(time_mm // geometry.max_stave_length)
    stave = stave_index % geometry.staves_per_page
    page_index = stave_index // geometry.staves_per_page
    x_in_page = (time_mm - (stave_index * geometry.max_stave_length)) + params.margin
    return page_index, stave, x_in_page


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

    geometry = compute_stave_geometry(tune, music_box, params)
    staves_per_page = geometry.staves_per_page
    stave_width = geometry.stave_width
    max_stave_length = geometry.max_stave_length
    pages = geometry.pages

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
                    note_id=note.id,
                )
                if note.lyric:
                    # Above the topmost lane (y < every lane's y = line_offset +
                    # lane*pitch for lane >= 0), so the syllable can never land on
                    # a punched hole - see the Phase 5 lyric-placement requirement.
                    renderer.text(
                        note.lyric,
                        note_time + params.margin,
                        line_offset - params.font_size,
                        "black",
                        params.font_size,
                    )
        renderer.save()

    if transpose.fit_fraction != 1.0:
        warnings.append("PERFECT TRANSPOSITION NOT FOUND")

    return Diagnostics(
        min_note_distance_mm=min_note_distance,
        transpose_fit_fraction=transpose.fit_fraction,
        warnings=warnings,
    )
