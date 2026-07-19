import numpy as np
import sounddevice as sd

from punchbox.layout import nearest_lane

from .synth import SAMPLE_RATE
from .synth import TONE_DURATION_SECONDS
from .synth import midi_to_freq
from .synth import render_tine_pluck


class AudioEngine:
    """Pre-renders the whole tune into one PCM buffer - each note placed at its
    mm position along the strip (the same math the visual layout uses),
    converted to seconds via the music box's feed rate - and plays it back
    through a single OutputStream with a read-pointer callback. Unlike
    sounddevice's simple play()/stop() helpers, moving the read pointer gives
    real pause/seek instead of only "restart from the beginning".
    """

    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._buffer = np.zeros(0, dtype=np.float32)
        self._position = 0
        self._stream = None

    def build_buffer(self, tune, music_box, params, transpose, feed_rate_mm_per_s=None):
        """Render `tune` to PCM, replacing any previous buffer. Returns the new
        buffer's duration in seconds. Each note is snapped to its box lane the
        same way draw_layout's dots are, so the preview matches what prints.
        """
        feed_rate = feed_rate_mm_per_s or music_box.feed_rate_mm_per_s
        notes = tune.sorted_notes()
        self.stop()

        if not notes:
            self._buffer = np.zeros(0, dtype=np.float32)
            return 0.0

        last_start_mm = notes[-1].start * params.mm_per_quarter
        total_seconds = (last_start_mm / feed_rate) + TONE_DURATION_SECONDS
        n_samples = int(total_seconds * self.sample_rate) + 1
        buffer = np.zeros(n_samples, dtype=np.float32)

        for note in notes:
            lane, _exact = nearest_lane(music_box, note.pitch + transpose.shift)
            freq = midi_to_freq(music_box.note_data[lane])
            tone = render_tine_pluck(freq, self.sample_rate)

            start_mm = note.start * params.mm_per_quarter
            start_sample = int((start_mm / feed_rate) * self.sample_rate)
            end_sample = min(start_sample + len(tone), n_samples)
            length = end_sample - start_sample
            if length > 0:
                buffer[start_sample:end_sample] += tone[:length]

        peak = float(np.max(np.abs(buffer))) if buffer.size else 0.0
        if peak > 1.0:
            buffer = buffer / peak

        self._buffer = buffer
        return self.duration_seconds()

    def duration_seconds(self):
        return len(self._buffer) / self.sample_rate

    def current_position_seconds(self):
        return self._position / self.sample_rate

    def seek(self, seconds):
        self._position = max(0, min(int(seconds * self.sample_rate), len(self._buffer)))

    def is_playing(self):
        return self._stream is not None

    def read_chunk(self, frame_count):
        """Pull `frame_count` samples from the current position, advancing it,
        zero-padded if the buffer runs out before `frame_count` samples. This is
        exactly what the playback callback below calls on every audio-thread
        tick, kept as its own method so the chunking/position bookkeeping can be
        unit tested without a working audio device.
        """
        start = self._position
        end = min(start + frame_count, len(self._buffer))
        chunk = self._buffer[start:end]
        self._position = end
        finished = end >= len(self._buffer)
        if len(chunk) < frame_count:
            chunk = np.pad(chunk, (0, frame_count - len(chunk)))
        return chunk, finished

    def play(self):
        if self._buffer.size == 0 or self._position >= len(self._buffer):
            return
        self.pause()

        def callback(outdata, frames, time_info, status):
            chunk, finished = self.read_chunk(frames)
            outdata[:, 0] = chunk
            if finished:
                raise sd.CallbackStop()

        def finished_callback():
            # Fires (on a sounddevice-managed thread) whenever the stream stops,
            # including via the callback's own CallbackStop above - without this,
            # is_playing() would keep reporting True after playback finishes on
            # its own, since nothing else clears self._stream in that case.
            self._stream = None

        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=callback,
            finished_callback=finished_callback,
        )
        self._stream.start()

    def pause(self):
        # Grab and clear the reference before touching it: finished_callback
        # (above) can null out self._stream from a different thread the moment
        # playback finishes on its own, so operate on a local to avoid a race
        # where self._stream turns None between the .stop() and .close() calls.
        stream = self._stream
        self._stream = None
        if stream is not None:
            stream.stop()
            stream.close()

    def stop(self):
        self.pause()
        self._position = 0
