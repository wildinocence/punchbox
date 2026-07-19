from abc import ABC
from abc import abstractmethod


class OMREngine(ABC):
    """Recognizes one page image and returns the path to a MusicXML file
    written into `output_dir`.

    Implementations shell out to an external OMR tool - there's no in-process
    Python OMR API worth binding to directly, and treating every engine as "run
    a process, read back a MusicXML file" is what lets a second engine (e.g.
    Audiveris, more mature but AGPL-licensed and JVM-based) be added later as
    just another OMREngine subclass, without touching anything upstream of it.
    """

    @abstractmethod
    def recognize_page(self, image_path, output_dir):
        ...
