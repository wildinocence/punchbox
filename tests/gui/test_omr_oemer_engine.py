import subprocess
from unittest.mock import patch

from punchbox_gui.omr.oemer_engine import OemerEngine


def _fake_completed(returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


def test_recognize_page_invokes_oemer_with_expected_arguments(tmp_path):
    image_path = tmp_path / "page000.png"
    image_path.write_bytes(b"fake png bytes")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "page000.musicxml").write_text("<score-partwise/>")

    with patch("subprocess.run", return_value=_fake_completed()) as mock_run:
        result = OemerEngine().recognize_page(image_path, output_dir)

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "oemer"
    assert str(image_path) in args
    assert "-o" in args
    assert str(output_dir) in args
    assert result == output_dir / "page000.musicxml"


def test_recognize_page_raises_on_nonzero_exit(tmp_path):
    image_path = tmp_path / "page000.png"
    image_path.write_bytes(b"fake png bytes")

    with patch("subprocess.run", return_value=_fake_completed(returncode=1, stderr="boom")):
        try:
            OemerEngine().recognize_page(image_path, tmp_path)
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "boom" in str(exc)


def test_recognize_page_raises_if_expected_output_file_is_missing(tmp_path):
    image_path = tmp_path / "page000.png"
    image_path.write_bytes(b"fake png bytes")
    # subprocess "succeeds" but doesn't actually leave a .musicxml behind -
    # oemer's real output naming was confirmed by reading its source, but a
    # future oemer version changing that convention should fail loudly here
    # rather than silently returning a path to nothing.
    with patch("subprocess.run", return_value=_fake_completed()):
        try:
            OemerEngine().recognize_page(image_path, tmp_path)
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "did not produce" in str(exc)


def test_recognize_page_creates_output_dir_if_missing(tmp_path):
    image_path = tmp_path / "page000.png"
    image_path.write_bytes(b"fake png bytes")
    output_dir = tmp_path / "does" / "not" / "exist"

    def fake_run(args, **kwargs):
        (output_dir / "page000.musicxml").write_text("<score-partwise/>")
        return _fake_completed()

    with patch("subprocess.run", side_effect=fake_run):
        OemerEngine().recognize_page(image_path, output_dir)

    assert output_dir.exists()
