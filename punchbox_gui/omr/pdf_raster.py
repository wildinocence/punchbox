import tempfile
from pathlib import Path

import fitz


def rasterize_pdf(pdf_path, dpi=300, output_dir=None):
    """Render each page of a PDF to a PNG at `dpi`, returning the written paths
    in page order. OMR models expect a clean, reasonably high-resolution raster
    image, not a vector PDF page.
    """
    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="punchbox_omr_")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix)
        out_path = output_dir / "page{:03d}.png".format(i)
        pix.save(str(out_path))
        paths.append(out_path)
    return paths
