import re
import asyncio
import time
from typing import Callable, Optional
from .audio import record_audio, save_wav, play_audio
from .speech_to_text import SpeechToText
from .tts import TextToSpeech
from brain.llm import generate_response
from config import WHISPER_MODEL


class VoiceManager:
    def __init__(self, stt_model=WHISPER_MODEL, tts_voice="af_heart",
                 on_event: Optional[Callable[[dict], None]] = None):
        self.stt = SpeechToText(model_name=stt_model)
        self.tts = TextToSpeech(voice=tts_voice)
        self.on_event = on_event or (lambda e: None)

    def _emit(self, state: str, **extra):
        self.on_event({"state": state, **extra})

    def listen(self, duration_seconds: Optional[float] = None, save_debug_audio=False, save_path="test_recording.wav"):
        """
        Records audio. If duration_seconds is None, automatically records until
        the user stops speaking (Voice Activity Detection + Silence Detection).
        """
        audio = record_audio(duration_seconds=duration_seconds)
        if save_debug_audio and audio is not None and len(audio) > 0:
            save_wav(audio, save_path)
        return audio

    def speech_to_text(self, audio) -> str:
        return self.stt.transcribe(audio)

    def speak(self, text: str, on_start: Optional[Callable[[], None]] = None):
        """
        Synthesizes the complete natural neural audio waveform first,
        then calls on_start() so the text card pops up and the speaker starts
        talking at the EXACT SAME INSTANT with continuous, seamless audio flow
        and ZERO pauses between sentences.
        """
        audio, sample_rate = self.tts.synthesize(text)
        if on_start:
            on_start()
        if audio is not None and len(audio) > 0:
            play_audio(audio, sample_rate)

    async def run_turn(self, duration_seconds: Optional[float] = None, save_debug_audio=False) -> dict:
        start = time.monotonic()
        loop = asyncio.get_event_loop()
        try:
            # --- record ---
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
            # the user's chat bubble and shows the Thinking... indicator.
            self._emit("thinking", transcript=transcript)
            reply = await generate_response(transcript)

            # Synchronize text pop-up with audio start:
            # on_start fires the exact moment the complete audio waveform is ready
            # so the text card pops up and speech plays simultaneously with 0ms delay!
            def _on_audio_start():
                self._emit("speaking", reply=reply)

            await loop.run_in_executor(None, self.speak, reply, _on_audio_start)

            self._emit("idle")
            return {"success": True, "transcript": transcript, "reply": reply,
                    "error": None, "latency_ms": int((time.monotonic() - start) * 1000)}

        except Exception as e:
            self._emit("idle")
            return {"success": False, "transcript": "", "reply": "",
                    "error": str(e), "latency_ms": int((time.monotonic() - start) * 1000)}
