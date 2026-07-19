import pytest

from punchbox.config import MusicBox
from punchbox.layout import LayoutParams
from punchbox.layout import compute_stave_geometry
from punchbox.layout import draw_layout
from punchbox.layout import nearest_lane
from punchbox.layout import scene_point_to_note
from punchbox.layout import stave_position_for_time_mm
from punchbox.model import NoteEvent
from punchbox.model import Tune
from punchbox.transpose import TransposeResult


class FakeRenderer:
    def __init__(self):
        self.calls = []
        self.pages = 0
        self.saves = 0

    def new_page(self, width, height):
        self.pages += 1
        self.calls.append(("new_page", width, height))

    def line(self, x1, y1, x2, y2):
        self.calls.append(("line", x1, y1, x2, y2))

    def circle(self, x, y, radius, color, note_id=None):
        self.calls.append(("circle", x, y, radius, color, note_id))

    def text(self, content, x, y, color, font_size):
        self.calls.append(("text", content, x, y, color, font_size))

    def save(self):
        self.saves += 1
        self.calls.append(("save",))

    def circles(self):
        return [c for c in self.calls if c[0] == "circle"]


def _box(note_data, reverse=False, pitch=2.0, note_collision=1.0):
    return MusicBox(
        {
            "note_data": note_data,
            "reverse": reverse,
            "pitch": pitch,
            "note_collision": note_collision,
        }
    )


def test_nearest_lane_exact_match():
    box = _box([60, 62, 64, 65, 67])
    lane, exact = nearest_lane(box, 64)
    assert (lane, exact) == (2, True)


def test_nearest_lane_snaps_up_to_next_available():
    box = _box([60, 62, 64, 65, 67])
    lane, exact = nearest_lane(box, 63)
    assert (lane, exact) == (2, False)  # snaps up to 64


def test_nearest_lane_below_range_snaps_to_lowest():
    box = _box([60, 62, 64, 65, 67])
    lane, exact = nearest_lane(box, 50)
    assert (lane, exact) == (0, False)


def test_nearest_lane_above_range_snaps_to_highest():
    box = _box([60, 62, 64, 65, 67])
    lane, exact = nearest_lane(box, 100)
    assert (lane, exact) == (4, False)


def test_nearest_lane_reverse_flag_changes_displayed_lane_not_choice():
    # reverse only changes which lane index a given pitch decision lands on -
    # the "nearest available pitch" choice itself is always based on true pitch order.
    forward = _box([60, 62, 64, 65, 67], reverse=False)
    reversed_box = _box([60, 62, 64, 65, 67], reverse=True)
    assert reversed_box.note_data == [67, 65, 64, 62, 60]

    lane_forward, _ = nearest_lane(forward, 61)
    lane_reversed, _ = nearest_lane(reversed_box, 61)
    assert lane_forward == 1  # 62 is at index 1 in ascending order
    assert lane_reversed == 3  # 62 is at index 3 in the reversed array


def test_draw_layout_places_dots_and_flags_inexact_matches():
    box = _box([60, 62, 64], pitch=2.0, note_collision=1.0)
    note_a = NoteEvent(pitch=60, start=0)
    note_b = NoteEvent(pitch=62, start=1)
    note_c = NoteEvent(pitch=65, start=2)  # not in note_data -> snaps up to 64, red
    tune = Tune(title="t", notes=[note_a, note_b, note_c])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    transpose = TransposeResult(shift=0, fit_fraction=2 / 3)
    renderer = FakeRenderer()

    diagnostics = draw_layout(tune, box, params, transpose, renderer, name="Test Tune")

    assert renderer.pages == 1
    assert renderer.saves == 1
    assert renderer.circles() == [
        ("circle", 5.0, 5.0, 1.0, "black", note_a.id),
        ("circle", 15.0, 7.0, 1.0, "black", note_b.id),
        ("circle", 25.0, 9.0, 1.0, "red", note_c.id),
    ]
    assert "PERFECT TRANSPOSITION NOT FOUND" in diagnostics.warnings


def test_draw_layout_no_warning_on_perfect_transpose():
    box = _box([60, 62, 64])
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0)])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    transpose = TransposeResult(shift=0, fit_fraction=1.0)

    diagnostics = draw_layout(tune, box, params, transpose, FakeRenderer())

    assert "PERFECT TRANSPOSITION NOT FOUND" not in diagnostics.warnings


def test_draw_layout_flags_note_collision():
    box = _box([60, 62, 64], note_collision=6.0)
    tune = Tune(
        title="t",
        notes=[NoteEvent(pitch=60, start=0.0), NoteEvent(pitch=60, start=0.5)],
    )
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    transpose = TransposeResult(shift=0, fit_fraction=1.0)

    diagnostics = draw_layout(tune, box, params, transpose, FakeRenderer())

    assert diagnostics.min_note_distance_mm == 5.0
    assert any("SOME NOTES MAY NOT PLAY" in w for w in diagnostics.warnings)


def test_compute_stave_geometry_gives_empty_tune_at_least_one_page():
    # A freshly-created tune with zero notes still needs somewhere for the
    # piano-roll editor to click to add the first note.
    box = _box([60, 62, 64])
    tune = Tune(title="t", notes=[])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)

    geometry = compute_stave_geometry(tune, box, params)

    assert geometry.pages == 1
    assert geometry.staves_per_page >= 1


def test_scene_point_to_note_round_trips_draw_layout_dot_positions():
    # Same fixture as test_draw_layout_places_dots_and_flags_inexact_matches:
    # its three dots land at (5,5)->lane0, (15,7)->lane1, (25,9)->lane2. Feeding
    # those exact coordinates back through scene_point_to_note must recover the
    # same lanes - if these two ever disagree, clicking a note wouldn't hit it.
    box = _box([60, 62, 64], pitch=2.0)
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0)])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    geometry = compute_stave_geometry(tune, box, params)

    assert scene_point_to_note(0, 5.0, 5.0, box, params, geometry) == (60, 0.0)
    assert scene_point_to_note(0, 15.0, 7.0, box, params, geometry) == (62, 1.0)
    assert scene_point_to_note(0, 25.0, 9.0, box, params, geometry) == (64, 2.0)


def test_scene_point_to_note_rejects_clicks_outside_any_lane_or_stave():
    box = _box([60, 62, 64], pitch=2.0)
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0)])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    geometry = compute_stave_geometry(tune, box, params)

    assert scene_point_to_note(0, -1.0, 5.0, box, params, geometry) is None  # left of margin
    assert scene_point_to_note(0, 5.0, 0.5, box, params, geometry) is None  # above top lane
    assert scene_point_to_note(0, 5.0, 999.0, box, params, geometry) is None  # off the page


def test_stave_position_for_time_mm_matches_draw_layout_dot_x():
    # Same fixture as the scene_point_to_note round-trip test: note_b's dot
    # (start=1.0 qlen, mm_per_quarter=10.0) lands at x=15.0 on stave 0, page 0.
    box = _box([60, 62, 64], pitch=2.0)
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0)])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    geometry = compute_stave_geometry(tune, box, params)

    page_index, stave, x_in_page = stave_position_for_time_mm(10.0, params, geometry)

    assert (page_index, stave, x_in_page) == (0, 0, 15.0)


def test_stave_position_for_time_mm_wraps_to_next_stave_and_page():
    box = _box([60, 62], pitch=2.0)
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0)])
    params = LayoutParams(mm_per_quarter=10.0, margin=2.0, page_width=30.0, page_height=10.0)
    geometry = compute_stave_geometry(tune, box, params)
    assert geometry.staves_per_page == 2  # sanity check on the fixture

    # max_stave_length = 30 - 2*2 = 26mm; a time just past that wraps to stave 1.
    page_index, stave, x_in_page = stave_position_for_time_mm(27.0, params, geometry)
    assert (page_index, stave) == (0, 1)
    assert x_in_page == pytest.approx(1.0 + params.margin)

    # far enough along to wrap past staves_per_page onto the next page.
    time_past_one_page = geometry.max_stave_length * geometry.staves_per_page + 1.0
    page_index, stave, _ = stave_position_for_time_mm(time_past_one_page, params, geometry)
    assert (page_index, stave) == (1, 0)
