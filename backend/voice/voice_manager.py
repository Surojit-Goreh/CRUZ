import asyncio
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
        loop = asyncio.get_event_loop()
        try:
            # --- record ---
            # listen()/speak()/speech_to_text() are blocking, synchronous
            # calls (real-time audio I/O + local model inference). Running
            # them directly on the event loop freezes every websocket in
            # the app for their entire duration, which also delays the
            # _emit() events below from actually reaching the client until
            # the blocking call returns. run_in_executor moves the blocking
            # work to a thread so the loop stays free to flush events
            # immediately, in the order they happen.
            self._emit("listening")
            audio = await loop.run_in_executor(
                None, self.listen, duration_seconds, save_debug_audio
            )

            # --- transcribe ---
            self._emit("transcribing")
            transcript = await loop.run_in_executor(None, self.speech_to_text, audio)

            if not transcript.strip():
                self._emit("idle")
                return {"success": False, "transcript": "", "reply": "",
                        "error": "No speech detected",
                        "latency_ms": int((time.monotonic() - start) * 1000)}

            # Emitted the moment STT finishes — the client shows this as
            # the user's chat bubble right away, well before the LLM
            # reply or the audio playback happen.
            self._emit("thinking", transcript=transcript)
            reply = await generate_response(transcript)

            # Emitted the moment the LLM reply is ready — the client shows
            # this as the assistant's chat bubble BEFORE we start playing
            # the spoken audio below, so text and speech land together
            # instead of speech-then-text.
            self._emit("speaking", reply=reply)
            await loop.run_in_executor(None, self.speak, reply)

            self._emit("idle")
            return {"success": True, "transcript": transcript, "reply": reply,
                    "error": None, "latency_ms": int((time.monotonic() - start) * 1000)}

        except Exception as e:
            self._emit("idle")
            return {"success": False, "transcript": "", "reply": "",
                    "error": str(e), "latency_ms": int((time.monotonic() - start) * 1000)}
