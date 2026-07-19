from abc import ABC
from abc import abstractmethod


class Renderer(ABC):
    """Draws a punch-strip layout. All coordinates are millimeters:
    x = position along the strip's time axis, y = position along the note-lane axis.

    Implemented by render_svg.SvgRenderer for file export; a QPainter-backed
    implementation drives on-screen preview and printing in the GUI (later phase).
    """

    @abstractmethod
    def new_page(self, width, height):
        ...

    @abstractmethod
    def line(self, x1, y1, x2, y2):
        ...

    @abstractmethod
    def circle(self, x, y, radius, color, note_id=None):
        """Draw a note dot. `note_id` (NoteEvent.id) is only meaningful to
        interactive renderers (e.g. the GUI's editable piano-roll) that need to
        map a drawn dot back to the note it represents; other backends ignore it.
        """
        ...

    @abstractmethod
    def text(self, content, x, y, color, font_size):
        ...

    @abstractmethod
    def save(self):
        ...


class RotatedRenderer(Renderer):
    """Wraps another Renderer, swapping x<->y (and width<->height) before
    delegating.

    draw_layout's own geometry is landscape: x=time (spans page_width), y=note
    lane (spans page_height, stacking multiple staves if a page isn't tall
    enough for the whole tune). A real music-box paper strip is the opposite -
    narrow across the notes (e.g. 90mm for a 30-note box) and long along time
    (routinely 700mm+, fed through the box in one continuous, unbroken run).

    Rather than teach draw_layout two coordinate conventions, callers that need
    physically-accurate output (print, SVG/PDF export) wrap their real Renderer
    in this one; draw_layout's math and its tests stay exactly as they are.
    """

    def __init__(self, inner):
        self._inner = inner

    def new_page(self, width, height):
        self._inner.new_page(height, width)

    def line(self, x1, y1, x2, y2):
        self._inner.line(y1, x1, y2, x2)

    def circle(self, x, y, radius, color, note_id=None):
        self._inner.circle(y, x, radius, color, note_id=note_id)

    def text(self, content, x, y, color, font_size):
        self._inner.text(content, y, x, color, font_size)

    def save(self):
        self._inner.save()
