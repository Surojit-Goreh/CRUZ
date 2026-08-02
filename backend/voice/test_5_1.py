from .audio import record_audio, save_wav
from .speech_to_text import SpeechToText

def main():
    stt = SpeechToText(model_name="base.en")

    input("Press ENTER to start recording (5 seconds)...")
    audio = record_audio(duration_seconds=5)
    save_wav(audio, "test_recording.wav")

    print("📝 Transcribing...")
    text = stt.transcribe(audio)
    print("\n" + "=" * 40)
    print(f"TRANSCRIPT: {text}")
    print("=" * 40)

if __name__ == "__main__":
    main()