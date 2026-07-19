import os

from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QDoubleSpinBox
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QFormLayout
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QInputDialog
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QProgressDialog
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from punchbox.config import load_boxen_config
from punchbox.layout import draw_layout
from punchbox.midi_source import load_tune_from_midi
from punchbox.render_svg import SvgRenderer
from punchbox.renderer import RotatedRenderer

from .audio.engine import AudioEngine
from .editor.piano_roll_view import PianoRollView
from .omr.musicxml_to_tune import build_tune_from_pages
from .omr.musicxml_to_tune import part_names
from .omr.omr_worker import run_omr_in_background
from .print_export import print_controller
from .state import AppState

_PLAYHEAD_INTERVAL_MS = 33


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

        self.audio_engine = AudioEngine()
        self._playhead_timer = QTimer(self)
        self._playhead_timer.setInterval(_PLAYHEAD_INTERVAL_MS)
        self._playhead_timer.timeout.connect(self._update_playhead)

        self._omr_thread = None
        self._omr_worker = None
        self._omr_progress = None
        self._omr_pdf_path = None

        self.box_combo = QComboBox()
        self.box_combo.addItems(self.state.boxen_names)
        self.box_combo.currentTextChanged.connect(self._on_box_changed)

        self.mm_per_quarter_spin = QDoubleSpinBox()
        self.mm_per_quarter_spin.setRange(0.1, 1000.0)
        self.mm_per_quarter_spin.setValue(self.state.layout_params.mm_per_quarter)
        self.mm_per_quarter_spin.valueChanged.connect(self._on_mm_per_quarter_changed)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(1.0, 500.0)
        self.speed_spin.setSuffix(" mm/s")
        self.speed_spin.setValue(15.0)
        self.speed_spin.valueChanged.connect(self._on_speed_changed)

        self.setCentralWidget(self._build_central_widget())

        # Any state change re-renders the preview and rebuilds the audio buffer -
        # editing, loading a file, or tweaking a layout field all funnel through
        # the same refresh, so what plays always matches what's on screen.
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

        open_pdf_button = QPushButton("Open PDF (OMR)…")
        open_pdf_button.clicked.connect(self._open_pdf)

        export_button = QPushButton("Export SVG…")
        export_button.clicked.connect(self._export_svg)

        preview_button = QPushButton("Print Preview…")
        preview_button.clicked.connect(self._print_preview)

        print_button = QPushButton("Print…")
        print_button.clicked.connect(self._print)

        calibration_button = QPushButton("Print Calibration Ruler…")
        calibration_button.clicked.connect(self._print_calibration)

        play_button = QPushButton("▶ Play")
        play_button.clicked.connect(self._play)
        pause_button = QPushButton("⏸ Pause")
        pause_button.clicked.connect(self._pause)
        stop_button = QPushButton("⏹ Stop")
        stop_button.clicked.connect(self._stop)

        transport = QHBoxLayout()
        transport.addWidget(play_button)
        transport.addWidget(pause_button)
        transport.addWidget(stop_button)

        form = QFormLayout()
        form.addRow("Music box:", self.box_combo)
        form.addRow("mm per quarter:", self.mm_per_quarter_spin)
        form.addRow("Playback speed:", self.speed_spin)

        controls = QVBoxLayout()
        controls.addWidget(open_button)
        controls.addWidget(open_pdf_button)
        controls.addLayout(form)
        controls.addLayout(transport)
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
        self.speed_spin.blockSignals(True)
        self.speed_spin.setValue(self.state.music_box.feed_rate_mm_per_s)
        self.speed_spin.blockSignals(False)

    def _on_mm_per_quarter_changed(self, value):
        self.state.set_layout_params(mm_per_quarter=value)

    def _on_speed_changed(self, value):
        self._refresh_preview()

    def _open_midi(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open MIDI file", "", "MIDI files (*.mid *.midi)"
        )
        if not path:
            return
        self.state.set_tune(load_tune_from_midi(path))

    def _open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open sheet music PDF", "", "PDF files (*.pdf)"
        )
        if not path:
            return
        self._omr_pdf_path = path

        self._omr_progress = QProgressDialog("Starting OMR…", "Cancel", 0, 1, self)
        self._omr_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._omr_progress.setMinimumDuration(0)
        self._omr_progress.canceled.connect(self._cancel_omr)

        self._omr_thread, self._omr_worker = run_omr_in_background(
            path,
            on_progress=self._on_omr_progress,
            on_scores=self._on_omr_scores_ready,
            on_failed=self._on_omr_failed,
        )

    def _cancel_omr(self):
        if self._omr_worker is not None:
            self._omr_worker.cancel()

    def _on_omr_progress(self, current, total, message):
        if self._omr_progress is None:
            return
        self._omr_progress.setMaximum(max(total, 1))
        self._omr_progress.setValue(current)
        self._omr_progress.setLabelText(message)

    def _on_omr_scores_ready(self, scores):
        if self._omr_progress is not None:
            self._omr_progress.close()
            self._omr_progress = None
        if not scores:
            QMessageBox.warning(self, "OMR", "No pages were recognized in that PDF.")
            return

        names = part_names(scores[0])
        part_index = 0
        if len(names) > 1:
            # Required, not a nicety: jw.org piano/vocal arrangements commonly
            # have more than one part, and silently guessing which one is the
            # melody could punch the wrong line entirely.
            choice, ok = QInputDialog.getItem(
                self,
                "Choose the melody part",
                "This score has multiple parts - which one should become the punch strip?",
                names,
                0,
                False,
            )
            if not ok:
                return
            part_index = names.index(choice)

        title = os.path.splitext(os.path.basename(self._omr_pdf_path))[0]
        tune = build_tune_from_pages(scores, part_index=part_index, title=title)
        self.state.set_tune(tune)

    def _on_omr_failed(self, message):
        if self._omr_progress is not None:
            self._omr_progress.close()
            self._omr_progress = None
        QMessageBox.critical(self, "OMR failed", message)

    def _refresh_preview(self):
        if self.state.music_box is None:
            return
        self._stop()
        transpose = self.state.compute_transpose()
        diagnostics = self.piano_roll.display_layout(
            self.state.tune,
            self.state.music_box,
            self.state.layout_params,
            transpose,
            name=self.state.tune.title,
        )
        self._show_diagnostics(transpose, diagnostics)
        self.audio_engine.build_buffer(
            self.state.tune,
            self.state.music_box,
            self.state.layout_params,
            transpose,
            feed_rate_mm_per_s=self.speed_spin.value(),
        )

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
            RotatedRenderer(SvgRenderer(prefix)),
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

    def _play(self):
        if self.audio_engine.is_playing():
            return
        try:
            self.audio_engine.play()
        except Exception as exc:
            # Real hardware failures (no output device, driver in use elsewhere)
            # are the one case here worth catching at this boundary - letting an
            # exception from inside an audio callback thread surface as a raw
            # traceback would be a much worse experience than a message box.
            QMessageBox.warning(
                self, "Playback error", "Could not start audio playback:\n{}".format(exc)
            )
            return
        self._playhead_timer.start()

    def _pause(self):
        self.audio_engine.pause()
        self._playhead_timer.stop()

    def _stop(self):
        self.audio_engine.stop()
        self._playhead_timer.stop()
        self.piano_roll.clear_playhead()

    def _update_playhead(self):
        if not self.audio_engine.is_playing():
            self._playhead_timer.stop()
            self.piano_roll.clear_playhead()
            return
        time_mm = self.audio_engine.current_position_seconds() * self.speed_spin.value()
        self.piano_roll.set_playhead_time_mm(time_mm)
