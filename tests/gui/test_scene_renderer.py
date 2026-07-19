import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QGraphicsEllipseItem  # noqa: E402
from PySide6.QtWidgets import QGraphicsScene  # noqa: E402

from punchbox.config import MusicBox  # noqa: E402
from punchbox.layout import LayoutParams  # noqa: E402
from punchbox.layout import draw_layout  # noqa: E402
from punchbox.model import NoteEvent  # noqa: E402
from punchbox.model import Tune  # noqa: E402
from punchbox.transpose import TransposeResult  # noqa: E402
from punchbox_gui.editor.scene_renderer import SceneRenderer  # noqa: E402


def test_scene_renderer_places_one_ellipse_per_note(qapp):
    box = MusicBox({"note_data": [60, 62, 64], "pitch": 2.0, "note_collision": 1.0})
    tune = Tune(
        title="t",
        notes=[NoteEvent(pitch=60, start=0), NoteEvent(pitch=62, start=1)],
    )
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    transpose = TransposeResult(shift=0, fit_fraction=1.0)

    scene = QGraphicsScene()
    renderer = SceneRenderer(scene)
    draw_layout(tune, box, params, transpose, renderer, name="t")

    ellipses = [item for item in scene.items() if isinstance(item, QGraphicsEllipseItem)]
    assert len(ellipses) == 2


def test_scene_renderer_stacks_multiple_pages_vertically(qapp):
    box = MusicBox({"note_data": [60, 62], "pitch": 2.0, "note_collision": 1.0})
    # A long tune that needs more than one stave/page at a tiny page size.
    notes = [NoteEvent(pitch=60 if i % 2 == 0 else 62, start=i) for i in range(20)]
    tune = Tune(title="t", notes=notes)
    params = LayoutParams(mm_per_quarter=10.0, margin=2.0, page_width=30.0, page_height=10.0)
    transpose = TransposeResult(shift=0, fit_fraction=1.0)

    scene = QGraphicsScene()
    renderer = SceneRenderer(scene)
    draw_layout(tune, box, params, transpose, renderer, name="t")

    assert renderer._y_offset > 0  # more than one page was stacked
