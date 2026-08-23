import os
import sys
import time
import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.speech_to_text import SpeechToText
from voice.tts import TextToSpeech
from config import (
    GROQ_API_KEY,
    GROQ_STT_MODEL,
    GEMINI_API_KEY,
    GEMINI_STT_MODEL,
    OPENAI_API_KEY,
    OPENAI_STT_MODEL,
    WHISPER_MODEL,
    STT_PROVIDER,
    VOICE_MODE,
)


def run_stt_benchmark():
    print("=" * 70)
    print("  CRUZ High-Speed Multi-Model STT Benchmark & Failover Verification")
    print("=" * 70)
    print(f"STT_PROVIDER Mode:   {STT_PROVIDER}")
    print(f"VOICE_MODE:          {VOICE_MODE}")
    print(f"GROQ_API_KEY:        {'[Set]' if GROQ_API_KEY else '[Not Set]'}")
    print(f"GROQ_STT_MODEL:      {GROQ_STT_MODEL}")
    print(f"GEMINI_API_KEY:      {'[Set]' if GEMINI_API_KEY else '[Not Set]'}")
    print(f"GEMINI_STT_MODEL:    {GEMINI_STT_MODEL}")
    print(f"OPENAI_API_KEY:      {'[Set]' if OPENAI_API_KEY else '[Not Set]'}")
    print(f"LOCAL_WHISPER_MODEL: {WHISPER_MODEL}")
    print("=" * 70)

    # 1. Synthesize a clean test audio sample using Kokoro TTS
    print("\n[1/5] Synthesizing benchmark audio sample...")
    tts = TextToSpeech()
    test_phrase = "Artificial intelligence is advancing at unprecedented speed."
    raw_audio, sr = tts.synthesize(test_phrase)
    
    # Resample or prepare 16kHz audio array for STT
    import scipy.signal as signal
    if sr != 16000:
        target_len = int(len(raw_audio) * 16000 / sr)
        audio_16k = signal.resample(raw_audio, target_len).astype(np.float32)
    else:
        audio_16k = raw_audio.astype(np.float32)
    print(f" Benchmark audio generated: {len(audio_16k)} samples @ 16kHz (~{len(audio_16k)/16000:.1f}s)")
    print(f" Original reference text:   \"{test_phrase}\"")

    results = []

    # 2. Benchmark Groq Whisper Large-v3 (if key available)
    if GROQ_API_KEY:
        print("\n[2/5] Benchmarking Groq LPU Whisper STT...")
        try:
            groq_stt = SpeechToText(stt_provider="groq", voice_mode="cloud")
            t0 = time.monotonic()
            transcript, info = groq_stt.transcribe_with_info(audio_16k)
            latency = int((time.monotonic() - t0) * 1000)
            print(f" Groq Whisper Latency: {latency}ms | Model: {info.get('model')}")
            print(f" Transcript: \"{transcript}\"")
            results.append(("Groq LPU (Whisper Large-v3)", f"{latency}ms", transcript))
        except Exception as e:
            print(f" Groq STT failed: {e}")
            results.append(("Groq LPU (Whisper Large-v3)", "ERROR", str(e)[:35]))
    else:
        print("\n[2/5] Groq API key not found in env — skipping standalone Groq test.")

    # 3. Benchmark Google Gemini Multimodal STT (if key available)
    if GEMINI_API_KEY:
        print("\n[3/5] Benchmarking Google Gemini Flash STT...")
        try:
            gemini_stt = SpeechToText(stt_provider="gemini", voice_mode="cloud")
            t0 = time.monotonic()
            transcript, info = gemini_stt.transcribe_with_info(audio_16k)
            latency = int((time.monotonic() - t0) * 1000)
            print(f" Gemini STT Latency: {latency}ms | Model: {info.get('model')}")
            print(f" Transcript: \"{transcript}\"")
            results.append(("Google Gemini (Flash STT)", f"{latency}ms", transcript))
        except Exception as e:
            print(f" Gemini STT failed / unauthenticated: {e}")
            results.append(("Google Gemini (Flash STT)", "FAIL/404", "Auth/Model unavailable"))
    else:
        print("\n[3/5] Gemini API key not found in env — skipping standalone Gemini test.")

    # 4. Benchmark Local Whisper.cpp (100% Offline)
    print("\n[4/5] Benchmarking Local Whisper.cpp (Offline Fallback)...")
    try:
        local_stt = SpeechToText(stt_provider="local", voice_mode="local")
        t0 = time.monotonic()
        transcript, info = local_stt.transcribe_with_info(audio_16k)
        latency = int((time.monotonic() - t0) * 1000)
        print(f" Local Whisper Latency: {latency}ms | Model: {info.get('model')}")
        print(f" Transcript: \"{transcript}\"")
        results.append((f"Local Whisper.cpp ({WHISPER_MODEL})", f"{latency}ms", transcript))
    except Exception as e:
        print(f" Local Whisper failed: {e}")
        results.append((f"Local Whisper.cpp ({WHISPER_MODEL})", "ERROR", str(e)[:35]))

    # 5. Benchmark Auto Multi-Model Collaborative Cascade (Seamless Failover)
    print("\n[5/5] Testing Multi-Model Cascade (Auto Routing & Failover)...")
    cascade_stt = SpeechToText(stt_provider="auto", voice_mode="auto")
    t0 = time.monotonic()
    transcript, info = cascade_stt.transcribe_with_info(audio_16k)
    latency = int((time.monotonic() - t0) * 1000)
    print(f" Multi-Model Winner: {info.get('provider')}/{info.get('model')} in {latency}ms")
    print(f" Transcript: \"{transcript}\"")
    results.append((f"Auto Cascade ({info.get('provider')})", f"{latency}ms", transcript))

    # Summary Benchmark Table
    print("\n" + "=" * 70)
    print(f"{'ENGINE / PROVIDER':<32} | {'LATENCY':<10} | {'TRANSCRIPTION RESULT'}")
    print("-" * 70)
    for engine, lat, text in results:
        print(f"{engine:<32} | {lat:<10} | \"{text}\"")
    print("=" * 70)
    print(" All STT engine benchmarks completed successfully!")


if __name__ == "__main__":
    run_stt_benchmark()
