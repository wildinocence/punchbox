from punchbox.config import MusicBox
from punchbox.layout import LayoutParams
from punchbox.layout import draw_layout
from punchbox.layout import nearest_lane
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

    def circle(self, x, y, radius, color):
        self.calls.append(("circle", x, y, radius, color))

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
    tune = Tune(
        title="t",
        notes=[
            NoteEvent(pitch=60, start=0),
            NoteEvent(pitch=62, start=1),
            NoteEvent(pitch=65, start=2),  # not in note_data -> snaps up to 64, red
        ],
    )
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    transpose = TransposeResult(shift=0, fit_fraction=2 / 3)
    renderer = FakeRenderer()

    diagnostics = draw_layout(tune, box, params, transpose, renderer, name="Test Tune")

    assert renderer.pages == 1
    assert renderer.saves == 1
    assert renderer.circles() == [
        ("circle", 5.0, 5.0, 1.0, "black"),
        ("circle", 15.0, 7.0, 1.0, "black"),
        ("circle", 25.0, 9.0, 1.0, "red"),
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
