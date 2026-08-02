import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np

SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHANNELS = 1

def record_audio(duration_seconds=5, sample_rate=SAMPLE_RATE):
    print(f"🎤 Recording for {duration_seconds}s...")
    audio = sd.rec(
        int(duration_seconds * sample_rate),
        samplerate=sample_rate,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()  # block until recording finishes
    print("✅ Recording complete.")
    return audio.flatten()

def save_wav(audio: np.ndarray, path: str, sample_rate=SAMPLE_RATE):
    # scipy expects int16 for standard PCM wav
    int_audio = (audio * 32767).astype(np.int16)
    wavfile.write(path, sample_rate, int_audio)
    print(f"💾 Saved to {path}")

def play_audio(audio_array: np.ndarray, sample_rate: int):
    sd.play(audio_array, samplerate=sample_rate)
    sd.wait()