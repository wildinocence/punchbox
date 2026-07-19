from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QDoubleSpinBox
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QFormLayout
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from punchbox.config import load_boxen_config
from punchbox.layout import draw_layout
from punchbox.midi_source import load_tune_from_midi
from punchbox.render_svg import SvgRenderer

from .editor.piano_roll_view import PianoRollView
from .print_export import print_controller
from .state import AppState


class MainWindow(QMainWindow):
    def __init__(self, boxen_config_path):
        super().__init__()
        self.setWindowTitle("Punchbox")
        self.state = AppState(load_boxen_config(boxen_config_path))

        self.piano_roll = PianoRollView()
        self.diagnostics_label = QLabel(
            "Open a MIDI file, or click a lane on the right to start composing."
        )
        self.diagnostics_label.setWordWrap(True)

        self.box_combo = QComboBox()
        self.box_combo.addItems(self.state.boxen_names)
        self.box_combo.currentTextChanged.connect(self._on_box_changed)

        self.mm_per_quarter_spin = QDoubleSpinBox()
        self.mm_per_quarter_spin.setRange(0.1, 1000.0)
        self.mm_per_quarter_spin.setValue(self.state.layout_params.mm_per_quarter)
        self.mm_per_quarter_spin.valueChanged.connect(self._on_mm_per_quarter_changed)

        self.setCentralWidget(self._build_central_widget())

        # Any state change re-renders the preview - editing, loading a file, or
        # tweaking a layout field all funnel through the same refresh.
        self.state.tuneChanged.connect(self._refresh_preview)
        self.state.musicBoxChanged.connect(self._refresh_preview)
        self.state.layoutParamsChanged.connect(self._refresh_preview)

        self.piano_roll.noteAddRequested.connect(self.state.add_note)
        self.piano_roll.noteMoveRequested.connect(self.state.move_note)
        self.piano_roll.notesDeleteRequested.connect(self.state.delete_notes)

        if self.state.boxen_names:
            self.box_combo.setCurrentText(self.state.boxen_names[0])
            self.state.set_music_box(self.state.boxen_names[0])

    def _build_central_widget(self):
        open_button = QPushButton("Open MIDI…")
        open_button.clicked.connect(self._open_midi)

        export_button = QPushButton("Export SVG…")
        export_button.clicked.connect(self._export_svg)

        preview_button = QPushButton("Print Preview…")
        preview_button.clicked.connect(self._print_preview)

        print_button = QPushButton("Print…")
        print_button.clicked.connect(self._print)

        calibration_button = QPushButton("Print Calibration Ruler…")
        calibration_button.clicked.connect(self._print_calibration)

        form = QFormLayout()
        form.addRow("Music box:", self.box_combo)
        form.addRow("mm per quarter:", self.mm_per_quarter_spin)

        controls = QVBoxLayout()
        controls.addWidget(open_button)
        controls.addLayout(form)
        controls.addWidget(export_button)
        controls.addWidget(preview_button)
        controls.addWidget(print_button)
        controls.addWidget(calibration_button)
        controls.addWidget(self.diagnostics_label)
        controls.addStretch(1)

        controls_widget = QWidget()
        controls_widget.setLayout(controls)
        controls_widget.setFixedWidth(260)

        layout = QHBoxLayout()
        layout.addWidget(controls_widget)
        layout.addWidget(self.piano_roll, stretch=1)

        central = QWidget()
        central.setLayout(layout)
        return central

    def _on_box_changed(self, name):
        if not name:
            return
        self.state.set_music_box(name)

    def _on_mm_per_quarter_changed(self, value):
        self.state.set_layout_params(mm_per_quarter=value)

    def _open_midi(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open MIDI file", "", "MIDI files (*.mid *.midi)"
        )
        if not path:
            return
        self.state.set_tune(load_tune_from_midi(path))

    def _refresh_preview(self):
        if self.state.music_box is None:
            return
        transpose = self.state.compute_transpose()
        diagnostics = self.piano_roll.display_layout(
            self.state.tune,
            self.state.music_box,
            self.state.layout_params,
            transpose,
            name=self.state.tune.title,
        )
        self._show_diagnostics(transpose, diagnostics)

    def _show_diagnostics(self, transpose, diagnostics):
        lines = [
            "Transpose: {} ({:.0f}% fit)".format(transpose.shift, transpose.fit_fraction * 100)
        ]
        if diagnostics.min_note_distance_mm is not None:
            lines.append("Min note distance: {:.2f}mm".format(diagnostics.min_note_distance_mm))
        lines.extend(diagnostics.warnings)
        self.diagnostics_label.setText("\n".join(lines))

    def _export_svg(self):
        if self.state.music_box is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export SVG", "output", "SVG files (*.svg)")
        if not path:
            return
        prefix = path[:-4] if path.endswith(".svg") else path
        transpose = self.state.compute_transpose()
        draw_layout(
            self.state.tune,
            self.state.music_box,
            self.state.layout_params,
            transpose,
            SvgRenderer(prefix),
            name=self.state.tune.title,
        )

    def _print(self):
        if self.state.music_box is None:
            return
        transpose = self.state.compute_transpose()
        print_controller.print_tune(
            self,
            self.state.tune,
            self.state.music_box,
            self.state.layout_params,
            transpose,
            name=self.state.tune.title,
        )

    def _print_preview(self):
        if self.state.music_box is None:
            return
        transpose = self.state.compute_transpose()
        print_controller.preview_tune(
            self,
            self.state.tune,
            self.state.music_box,
            self.state.layout_params,
            transpose,
            name=self.state.tune.title,
        )

    def _print_calibration(self):
        print_controller.print_calibration_ruler(self)
