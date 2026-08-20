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
    """Plays audio array through default sound output device."""
    sd.play(audio_array, samplerate=sample_rate)
    sd.wait()