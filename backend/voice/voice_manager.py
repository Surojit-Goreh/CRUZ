import time
from typing import Callable, Optional
from .audio import record_audio, save_wav, play_audio
from .speech_to_text import SpeechToText
from .tts import TextToSpeech
from brain.llm import generate_response


class VoiceManager:
    def __init__(self, stt_model="base.en", tts_voice="af_heart",
                 on_event: Optional[Callable[[dict], None]] = None):
        self.stt = SpeechToText(model_name=stt_model)
        self.tts = TextToSpeech(voice=tts_voice)
        self.on_event = on_event or (lambda e: None)

    def _emit(self, state: str, **extra):
        self.on_event({"state": state, **extra})

    def listen(self, duration_seconds=5, save_debug_audio=False, save_path="test_recording.wav"):
        audio = record_audio(duration_seconds=duration_seconds)
        if save_debug_audio:
            save_wav(audio, save_path)
        return audio

    def speech_to_text(self, audio) -> str:
        return self.stt.transcribe(audio)

    def speak(self, text: str):
        audio, sample_rate = self.tts.synthesize(text)
        if audio.size > 0:
            play_audio(audio, sample_rate)

    async def run_turn(self, duration_seconds=5, save_debug_audio=False) -> dict:
        start = time.monotonic()
        try:
            self._emit("listening")
            print("🎤 VoiceManager started")
            audio = self.listen(duration_seconds=duration_seconds, save_debug_audio=save_debug_audio)

            self._emit("transcribing")
            transcript = self.speech_to_text(audio)

            if not transcript.strip():
                self._emit("idle")
                return {"success": False, "transcript": "", "reply": "",
                        "error": "No speech detected",
                        "latency_ms": int((time.monotonic() - start) * 1000)}

            self._emit("thinking", transcript=transcript)
            reply = await generate_response(transcript)

            self._emit("speaking", reply=reply)
            self.speak(reply)

            self._emit("idle")
            return {"success": True, "transcript": transcript, "reply": reply,
                    "error": None, "latency_ms": int((time.monotonic() - start) * 1000)}

        except Exception as e:
            self._emit("idle")
            return {"success": False, "transcript": "", "reply": "",
                    "error": str(e), "latency_ms": int((time.monotonic() - start) * 1000)}