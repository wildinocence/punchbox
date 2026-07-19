import numpy as np

SAMPLE_RATE = 44100
TONE_DURATION_SECONDS = 0.6


def midi_to_freq(pitch):
    """MIDI note number -> frequency in Hz (A4=69=440Hz, 12-tone equal temperament)."""
    return 440.0 * (2.0 ** ((pitch - 69) / 12.0))


def render_tine_pluck(
    freq_hz,
    sample_rate=SAMPLE_RATE,
    duration=TONE_DURATION_SECONDS,
    decay=6.0,
    amplitude=0.3,
):
    """A short plucked-tine burst, not a MIDI/piano soundfont voice - deliberately
    modeling the actual physical sound source (a metal comb tooth plucked by a
    pin), not a generic synthesized note: a fundamental plus a quieter second
    harmonic under a fixed exponential decay envelope.

    The envelope is a fixed acoustic property of a real tine, independent of
    anything resembling a "note length" - callers never vary `duration`/`decay`
    per note, unlike a conventional ADSR synth voice.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    envelope = np.exp(-decay * t)
    fundamental = np.sin(2 * np.pi * freq_hz * t)
    second_harmonic = 0.3 * np.sin(2 * np.pi * freq_hz * 2 * t)
    tone = (fundamental + second_harmonic) * envelope * amplitude
    return tone.astype(np.float32)
