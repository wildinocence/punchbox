from punchbox.renderer import RotatedRenderer


class FakeRenderer:
    def __init__(self):
        self.calls = []

    def new_page(self, width, height):
        self.calls.append(("new_page", width, height))

    def line(self, x1, y1, x2, y2):
        self.calls.append(("line", x1, y1, x2, y2))

    def circle(self, x, y, radius, color, note_id=None):
        self.calls.append(("circle", x, y, radius, color, note_id))

    def text(self, content, x, y, color, font_size):
        self.calls.append(("text", content, x, y, color, font_size))

    def save(self):
        self.calls.append(("save",))


def test_rotated_renderer_swaps_page_dimensions():
    inner = FakeRenderer()
    RotatedRenderer(inner).new_page(700.0, 90.0)
    assert inner.calls == [("new_page", 90.0, 700.0)]


def test_rotated_renderer_swaps_line_axes():
    inner = FakeRenderer()
    RotatedRenderer(inner).line(1.0, 2.0, 3.0, 4.0)
    assert inner.calls == [("line", 2.0, 1.0, 4.0, 3.0)]


def test_rotated_renderer_swaps_circle_axes_and_keeps_note_id():
    inner = FakeRenderer()
    RotatedRenderer(inner).circle(1.0, 2.0, 0.5, "black", note_id=7)
    assert inner.calls == [("circle", 2.0, 1.0, 0.5, "black", 7)]


def test_rotated_renderer_swaps_text_position():
    inner = FakeRenderer()
    RotatedRenderer(inner).text("C4", 1.0, 2.0, "red", 1.0)
    assert inner.calls == [("text", "C4", 2.0, 1.0, "red", 1.0)]


def test_rotated_renderer_save_passes_through():
    inner = FakeRenderer()
    RotatedRenderer(inner).save()
    assert inner.calls == [("save",)]
