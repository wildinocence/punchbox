import svgwrite


def _mm(value):
    return "{}mm".format(value)


class SvgRenderer:
    """Renderer backend that writes one SVG file per page: '{output_prefix}{page}.svg'."""

    def __init__(self, output_prefix):
        self.output_prefix = output_prefix
        self._page_index = -1
        self._dwg = None

    def new_page(self, width, height):
        self._page_index += 1
        self._dwg = svgwrite.Drawing(
            "{}{}.svg".format(self.output_prefix, self._page_index),
            size=(_mm(width), _mm(height)),
        )

    def line(self, x1, y1, x2, y2):
        self._dwg.add(
            self._dwg.line(
                (_mm(x1), _mm(y1)),
                (_mm(x2), _mm(y2)),
                stroke=svgwrite.rgb(0, 0, 0, "%"),
                stroke_width=".1mm",
            )
        )

    def circle(self, x, y, radius, color):
        self._dwg.add(self._dwg.circle((_mm(x), _mm(y)), _mm(radius), fill=color))

    def text(self, content, x, y, color, font_size):
        self._dwg.add(
            self._dwg.text(content, insert=(_mm(x), _mm(y)), fill=color, font_size=_mm(font_size))
        )

    def save(self):
        self._dwg.save()
