import os
import sys
import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.speech_to_text import SpeechToText
from voice.tts import TextToSpeech
from voice.audio import play_audio, save_wav
from config import GEMINI_API_KEY, GEMINI_STT_MODEL, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE, VOICE_MODE

def test_voice_engines():
    print("=" * 60)
    print(" CRUZ Voice Engine Verification (Google AI Studio + Offline Fallback)")
    print("=" * 60)
    print(f"VOICE_MODE:         {VOICE_MODE}")
    print(f"GEMINI_API_KEY:     {'[Configured]' if GEMINI_API_KEY else '[Not Set]'}")
    print(f"GEMINI_STT_MODEL:   {GEMINI_STT_MODEL}")
    print(f"GEMINI_TTS_MODEL:   {GEMINI_TTS_MODEL}")
    print(f"GEMINI_TTS_VOICE:   {GEMINI_TTS_VOICE}")
    print("=" * 60)

    # 1. Test Text-to-Speech (TTS)
    print("\n--- 1. Testing Text-to-Speech (TTS) ---")
    tts = TextToSpeech()
    test_phrase = "Hello! CRUZ voice system is now equipped with Google AI Studio and local offline fallback."
    
    print(f"Synthesizing text: '{test_phrase}'...")
    audio_data, sample_rate = tts.synthesize(test_phrase)
    print(f"TTS result: {len(audio_data)} audio samples @ {sample_rate}Hz")
    assert len(audio_data) > 0, "TTS failed to produce audio waveform"
    print("TTS synthesis succeeded.")

    # 2. Test Speech-to-Text (STT)
    print("\n--- 2. Testing Speech-to-Text (STT) ---")
    stt = SpeechToText()
    
    # Use existing test_recording.wav if present, or test with generated TTS audio
    wav_path = os.path.join(os.path.dirname(__file__), "test_recording.wav")
    if os.path.exists(wav_path):
        import scipy.io.wavfile as wavfile
        sr, audio_input = wavfile.read(wav_path)
        if audio_input.dtype == np.int16:
            audio_input = audio_input.astype(np.float32) / 32768.0
        print(f"Transcribing {wav_path} ({len(audio_input)} samples @ {sr}Hz)...")
        transcript = stt.transcribe(audio_input)
        print(f"Transcription Result: \"{transcript}\"")
    else:
        print("No test_recording.wav found, synthesizing and transcribing synthetic test audio...")
        # Transcribe the audio generated in step 1 if 16kHz resampled or direct
        transcript = stt.transcribe(audio_data[:min(len(audio_data), sample_rate * 5)])
        print(f"Transcription Result: \"{transcript}\"")

    # 3. Test Explicit Local Offline Mode Fallback
    print("\n--- 3. Testing Offline (Local Only) Mode Fallback ---")
    offline_tts = TextToSpeech(voice_mode="local")
    offline_audio, offline_sr = offline_tts.synthesize("Testing local offline Kokoro synthesis.")
    print(f"Local Kokoro TTS Output: {len(offline_audio)} samples @ {offline_sr}Hz")
    assert len(offline_audio) > 0, "Local TTS failed"

    offline_stt = SpeechToText(voice_mode="local")
    if os.path.exists(wav_path):
        offline_transcript = offline_stt.transcribe(audio_input)
        print(f"Local Whisper STT Output: \"{offline_transcript}\"")

    print("\n" + "=" * 60)
    print(" All Voice Engine tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    test_voice_engines()
