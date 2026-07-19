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
