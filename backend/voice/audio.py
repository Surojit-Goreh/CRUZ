from typing import Optional
import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np

from .silence import record_until_silence

SAMPLE_RATE = 16000  # 16kHz for STT (Whisper and Gemini)
CHANNELS = 1


def record_audio(duration_seconds: Optional[float] = None, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Records audio from the microphone.

    - If duration_seconds is None (default): Records dynamically using Voice Activity Detection (VAD)
      and stops automatically when the user finishes speaking.
    - If duration_seconds is a positive float/int: Records for that exact fixed duration (legacy/manual mode).
    """
    if duration_seconds is None or duration_seconds <= 0:
        return record_until_silence(sample_rate=sample_rate)

    print(f"🎤 Recording for {duration_seconds}s (fixed duration)...")
    audio = sd.rec(
        int(duration_seconds * sample_rate),
        samplerate=sample_rate,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()  # block until recording finishes
    print("✅ Recording complete.")
    return audio.flatten()


def save_wav(audio: np.ndarray, path: str, sample_rate: int = SAMPLE_RATE):
    """Saves float32 numpy audio array as 16-bit PCM WAV file."""
    if audio.dtype in (np.float32, np.float64):
        int_audio = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    else:
        int_audio = audio.astype(np.int16)
    wavfile.write(path, sample_rate, int_audio)
    print(f"💾 Saved to {path}")


def play_audio(audio_array: np.ndarray, sample_rate: int):
    """Plays audio array through default sound output device synchronously."""
    if audio_array is None or len(audio_array) == 0:
        return
    sd.play(audio_array, samplerate=sample_rate)
    sd.wait()


import threading
import queue

class AudioPlayerQueue:
    """
    Sequential, non-blocking audio queue player.
    Enables streaming sentence chunks to be synthesized in parallel with playback,
    eliminating gaps and playing audio the instant the first sentence is synthesized.
    """

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._idle_event = threading.Event()
        self._idle_event.set()
        self._active_playing = False

    def _worker(self):
        while self._running:
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                with self._lock:
                    if self._queue.empty() and not self._active_playing:
                        self._idle_event.set()
                continue

            if item is None:  # Sentinel to stop
                self._queue.task_done()
                break

            audio_array, sample_rate, on_start, on_finish = item
            with self._lock:
                self._active_playing = True
                self._idle_event.clear()

            try:
                if on_start:
                    on_start()
                if audio_array is not None and len(audio_array) > 0:
                    sd.play(audio_array, samplerate=sample_rate)
                    sd.wait()
                if on_finish:
                    on_finish()
            except Exception as e:
                print(f"Audio playback error: {e}")
            finally:
                with self._lock:
                    self._active_playing = False
                    self._queue.task_done()
                    if self._queue.empty():
                        self._idle_event.set()

    def start(self):
        with self._lock:
            if not self._running:
                self._running = True
                self._idle_event.set()
                self._active_playing = False
                self._thread = threading.Thread(target=self._worker, daemon=True)
                self._thread.start()

    def enqueue(self, audio_array: np.ndarray, sample_rate: int,
                on_start: Optional[callable] = None, on_finish: Optional[callable] = None):
        """Pushes an audio chunk to the playback queue."""
        self.start()
        with self._lock:
            self._idle_event.clear()
        self._queue.put((audio_array, sample_rate, on_start, on_finish))

    def wait_until_idle(self, timeout: Optional[float] = None):
        """Blocks until all currently enqueued audio chunks have completely finished playing."""
        self._queue.join()
        self._idle_event.wait(timeout=timeout)


    def clear(self):
        """Clears pending playback items and stops currently playing audio."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except queue.Empty:
                    break
            try:
                sd.stop()
            except Exception:
                pass
            self._idle_event.set()

    def stop(self):
        """Stops the playback worker thread."""
        with self._lock:
            self._running = False
            self.clear()
            if self._thread and self._thread.is_alive():
                self._queue.put(None)
                self._thread.join(timeout=1.0)
                self._thread = None