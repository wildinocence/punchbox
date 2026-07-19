import pytest

fitz = pytest.importorskip("fitz")
Image = pytest.importorskip("PIL.Image")

from punchbox_gui.omr.pdf_raster import rasterize_pdf  # noqa: E402


def _make_pdf(path, page_count=2):
    doc = fitz.open()
    for _ in range(page_count):
        page = doc.new_page(width=200, height=300)
        page.insert_text((20, 20), "test page")
    doc.save(str(path))
    doc.close()


def test_rasterize_pdf_writes_one_png_per_page_in_order(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    _make_pdf(pdf_path, page_count=3)

    paths = rasterize_pdf(pdf_path, dpi=100, output_dir=tmp_path / "out")

    assert len(paths) == 3
    assert [p.name for p in paths] == ["page000.png", "page001.png", "page002.png"]
    for p in paths:
        assert p.exists()
        assert p.stat().st_size > 0


def test_rasterize_pdf_respects_dpi(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    _make_pdf(pdf_path, page_count=1)  # 200x300pt page

    low_res = rasterize_pdf(pdf_path, dpi=72, output_dir=tmp_path / "low")
    high_res = rasterize_pdf(pdf_path, dpi=300, output_dir=tmp_path / "high")

    low_width, _ = Image.open(low_res[0]).size
    high_width, _ = Image.open(high_res[0]).size
    assert high_width > low_width


def test_rasterize_pdf_creates_output_dir_if_missing(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    _make_pdf(pdf_path, page_count=1)
    out_dir = tmp_path / "does" / "not" / "exist"

    paths = rasterize_pdf(pdf_path, output_dir=out_dir)

    assert out_dir.exists()
    assert paths[0].exists()
