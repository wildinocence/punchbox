import os

from punchbox.config import MusicBox
from punchbox.config import load_boxen_config

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_music_box_reverses_note_data_when_configured():
    box = MusicBox({"note_data": [60, 62, 64], "reverse": True})
    assert box.note_data == [64, 62, 60]


def test_music_box_defaults():
    box = MusicBox({})
    assert box.pitch == 2.0
    assert box.note_collision == 5.0
    assert box.reverse is False


def test_punchbox_yaml_has_30note_box_matching_physical_template():
    config = load_boxen_config(os.path.join(REPO_ROOT, "punchbox.yaml"))
    box = MusicBox(config["boxen"]["30note"])
    assert len(box.note_data) == 30
    assert config["default_musicbox"] == "30note"
