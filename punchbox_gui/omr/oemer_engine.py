import subprocess
from pathlib import Path

from .engine_base import OMREngine


class OemerEngine(OMREngine):
    """Shells out to the `oemer` CLI (its only public interface).

    oemer names its output `{image-basename}.musicxml` inside the given output
    directory (confirmed by reading oemer/ete.py's extract() - not documented
    anywhere else). Its model weights (~hundreds of MB) download from GitHub
    on first run; nothing here handles that specially, the subprocess just
    takes a lot longer on a cold cache.
    """

    def recognize_page(self, image_path, output_dir):
        image_path = Path(image_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["oemer", str(image_path), "-o", str(output_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "oemer failed on {}: {}".format(image_path.name, result.stderr.strip())
            )

        musicxml_path = output_dir / (image_path.stem + ".musicxml")
        if not musicxml_path.exists():
            raise RuntimeError(
                "oemer did not produce the expected output file: {}".format(musicxml_path)
            )
        return musicxml_path
