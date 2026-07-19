import pytest

pytest.importorskip("PySide6")
pytest.importorskip("sounddevice")
np = pytest.importorskip("numpy")

from punchbox.config import MusicBox  # noqa: E402
from punchbox.layout import LayoutParams  # noqa: E402
from punchbox.model import NoteEvent  # noqa: E402
from punchbox.model import Tune  # noqa: E402
from punchbox.transpose import TransposeResult  # noqa: E402
from punchbox_gui.audio.engine import AudioEngine  # noqa: E402
from punchbox_gui.audio.synth import SAMPLE_RATE  # noqa: E402
from punchbox_gui.audio.synth import TONE_DURATION_SECONDS  # noqa: E402
from punchbox_gui.audio.synth import midi_to_freq  # noqa: E402
from punchbox_gui.audio.synth import render_tine_pluck  # noqa: E402


def _box(note_data, feed_rate=10.0):
    return MusicBox(
        {
            "note_data": note_data,
            "pitch": 2.0,
            "note_collision": 1.0,
            "feed_rate_mm_per_s": feed_rate,
        }
    )


def test_midi_to_freq_a4_is_440hz():
    assert midi_to_freq(69) == pytest.approx(440.0)


def test_midi_to_freq_octave_doubles_frequency():
    assert midi_to_freq(81) == pytest.approx(midi_to_freq(69) * 2)


def test_render_tine_pluck_has_fixed_length_and_decays():
    tone = render_tine_pluck(440.0)
    assert len(tone) == int(SAMPLE_RATE * TONE_DURATION_SECONDS)
    assert tone.dtype == np.float32
    half = len(tone) // 2
    # exponential decay envelope: the back half should be much quieter on average
    assert np.abs(tone[:half]).mean() > 5 * np.abs(tone[half:]).mean()


def test_build_buffer_of_empty_tune_is_silent():
    engine = AudioEngine()
    tune = Tune(title="t", notes=[])
    box = _box([60, 62, 64])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)

    duration = engine.build_buffer(tune, box, params, TransposeResult(shift=0, fit_fraction=0.0))

    assert duration == 0.0
    assert engine.duration_seconds() == 0.0


def test_build_buffer_places_notes_at_feed_rate_derived_times():
    engine = AudioEngine()
    box = _box([60, 62, 64], feed_rate=10.0)  # 10 mm/s
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0.0), NoteEvent(pitch=64, start=2.0)])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)
    transpose = TransposeResult(shift=0, fit_fraction=1.0)

    # second note: 2.0 qlen * 10mm/qlen = 20mm; at 10mm/s -> onset at t=2.0s
    duration = engine.build_buffer(tune, box, params, transpose)

    assert duration == pytest.approx(2.0 + TONE_DURATION_SECONDS, abs=0.01)
    # the first note's tone array is fixed-length (TONE_DURATION_SECONDS) with
    # nothing added beyond it, so well after it and well before the second note
    # the buffer must be *exactly* silent, not just quiet - a robust, non-flaky
    # check unlike sampling a still-decaying tail.
    quiet_sample = int(0.8 * engine.sample_rate)
    assert engine._buffer[quiet_sample] == 0.0
    onset_sample = int(2.0 * engine.sample_rate)
    assert np.abs(engine._buffer[onset_sample:onset_sample + 100]).max() > 0.05


def test_build_buffer_clamps_peak_to_avoid_clipping():
    engine = AudioEngine()
    box = _box([60], feed_rate=10.0)
    # ten identical simultaneous notes would sum well past 1.0 without clamping
    tune = Tune(title="t", notes=[NoteEvent(pitch=60, start=0.0) for _ in range(10)])
    params = LayoutParams(mm_per_quarter=10.0, margin=5.0, page_width=50.0, page_height=50.0)

    engine.build_buffer(tune, box, params, TransposeResult(shift=0, fit_fraction=1.0))

    assert np.abs(engine._buffer).max() == pytest.approx(1.0, abs=1e-6)


def test_seek_and_read_chunk_advance_position():
    engine = AudioEngine()
    engine._buffer = np.arange(1000, dtype=np.float32)

    chunk, finished = engine.read_chunk(100)

    assert list(chunk[:5]) == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert engine.current_position_seconds() == pytest.approx(100 / engine.sample_rate)
    assert finished is False


def test_read_chunk_pads_and_reports_finished_at_end_of_buffer():
    engine = AudioEngine()
    engine._buffer = np.ones(50, dtype=np.float32)
    engine._position = 40

    chunk, finished = engine.read_chunk(20)

    assert len(chunk) == 20
    assert list(chunk[:10]) == [1.0] * 10
    assert list(chunk[10:]) == [0.0] * 10
    assert finished is True


def test_seek_clamps_to_buffer_bounds():
    engine = AudioEngine()
    engine._buffer = np.zeros(100, dtype=np.float32)

    engine.seek(-5.0)
    assert engine._position == 0

    engine.seek(1000.0)
    assert engine._position == 100


def test_stop_resets_position_and_playing_state():
    engine = AudioEngine()
    engine._buffer = np.zeros(100, dtype=np.float32)
    engine._position = 50

    engine.stop()

    assert engine._position == 0
    assert engine.is_playing() is False
