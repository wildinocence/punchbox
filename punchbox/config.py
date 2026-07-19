import yaml


class MusicBox(object):
    def __init__(self, config):
        self.note_data = config.get(
            "note_data", [60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72]
        )
        self.reverse = config.get("reverse", False)
        self.pitch = config.get("pitch", 2.0)
        self.note_collision = config.get("note_collision", 5.0)
        if self.reverse:
            self.note_data = self.note_data[::-1]


def load_boxen_config(path):
    with open(path) as f:
        return yaml.safe_load(f)
