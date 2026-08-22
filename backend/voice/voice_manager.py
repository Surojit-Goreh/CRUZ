import re
import asyncio
import time
from typing import AsyncIterator, Callable, Optional
from .audio import record_audio, save_wav, play_audio, AudioPlayerQueue
from .speech_to_text import SpeechToText
from .tts import TextToSpeech, audio_to_base64_wav
from .sentence_chunker import stream_sentences, SentenceChunker
from brain.llm import generate_stream, generate_response
from services.model_router import model_router
from services.providers.classifier import detect_agent_mode_intent
from config import WHISPER_MODEL
from utils.logger import get_logger

logger = get_logger("voice.voice_manager")


class VoiceManager:
    def __init__(self, stt_model=WHISPER_MODEL, tts_voice="af_heart",
                 on_event: Optional[Callable[[dict], None]] = None):
        self.stt = SpeechToText(model_name=stt_model)
        self.tts = TextToSpeech(voice=tts_voice)
        self.on_event = on_event or (lambda e: None)
        self.audio_player = AudioPlayerQueue()

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

    def speech_to_text(self, audio_data) -> str:
        return self.stt.transcribe(audio_data)

    def speak(self, text: str, on_start: Optional[Callable[[], None]] = None):
        audio, sample_rate = self.tts.synthesize(text)
        if on_start:
            on_start()
        play_audio(audio, sample_rate)

    async def stream_reply_tts(self, token_stream: AsyncIterator[str]) -> str:
        """
        Consumes an LLM token stream asynchronously, chunks it into natural sentences,
        synthesizes each sentence into speech with Kokoro TTS, emits WebSocket audio events,
        and enqueues audio chunks to the audio player for gapless, overlapping playback.
        """
        full_reply = ""
        sentence_idx = 0
        loop = asyncio.get_event_loop()

        async for sentence in stream_sentences(token_stream):
            full_reply += (" " if full_reply else "") + sentence
            sentence_clean = re.sub(r"[*_`#~]", "", sentence).strip()
            # Clean internal command tokens from spoken TTS
            sentence_clean = re.sub(r"AGENT_MODE_SWITCH:\w+:\s*", "", sentence_clean).strip()
            if not sentence_clean:
                continue

            # Synthesize sentence speech in thread pool to avoid blocking async event loop
            audio_chunk, sample_rate = await loop.run_in_executor(
                None, self.tts.synthesize, sentence_clean
            )

            # Encode as base64 WAV for WebSocket streaming to frontend
            audio_b64 = audio_to_base64_wav(audio_chunk, sample_rate) if audio_chunk is not None else None

            provider_name = model_router.last_provider_info.get("provider_name")
            model_name = model_router.last_provider_info.get("model")

            # Push audio chunk and text event over WebSocket immediately
            self._emit(
                "speaking",
                text=sentence_clean,
                audio=audio_b64,
                sample_rate=sample_rate,
                sentence_index=sentence_idx,
                reply=full_reply,
                provider=provider_name,
                model=model_name,
            )

            # Enqueue audio chunk for gapless, non-blocking local playback
            if audio_chunk is not None and len(audio_chunk) > 0:
                self.audio_player.enqueue(audio_chunk, sample_rate)

            sentence_idx += 1

        # Wait for all enqueued audio chunks to finish playback
        if sentence_idx > 0:
            await loop.run_in_executor(None, self.audio_player.wait_until_idle)

        return full_reply

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

            # Check if user explicitly asked to change mode by voice
            intent_mode = detect_agent_mode_intent(transcript)
            if intent_mode:
                logger.info(f"Detected voice agent mode intent: '{intent_mode}' from transcript '{transcript}'")
                self._emit("agent_mode_changed", agent_mode=intent_mode)

            # Emitted the moment STT finishes — the client shows this as
            # the user's chat bubble and shows the Thinking... indicator.
            self._emit("thinking", transcript=transcript)

            # Stream LLM tokens -> chunk into sentences -> Kokoro TTS -> push WebSocket audio chunks
            token_stream = generate_stream(transcript, agent_mode=intent_mode or "auto")
            reply = await self.stream_reply_tts(token_stream)

            # Fallback if streaming produced empty reply
            if not reply.strip():
                reply = await generate_response(transcript, agent_mode=intent_mode or "auto")
                def _on_audio_start():
                    self._emit(
                        "speaking",
                        reply=reply,
                        provider=model_router.last_provider_info.get("provider_name"),
                        model=model_router.last_provider_info.get("model"),
                    )
                await loop.run_in_executor(None, self.speak, reply, _on_audio_start)

            # Check if agent mode switch token was emitted or detected in reply
            agent_mode_match = re.search(r"AGENT_MODE_SWITCH:(\w+):", reply)
            detected_mode = agent_mode_match.group(1) if agent_mode_match else intent_mode or detect_agent_mode_intent(reply)
            cleaned_reply = re.sub(r"AGENT_MODE_SWITCH:\w+:\s*", "", reply).strip() if agent_mode_match else reply

            if detected_mode:
                self._emit("agent_mode_changed", agent_mode=detected_mode)

            self._emit("idle")
            return {
                "success": True,
                "transcript": transcript,
                "reply": cleaned_reply,
                "error": None,
                "latency_ms": int((time.monotonic() - start) * 1000),
                "provider": model_router.last_provider_info.get("provider_name"),
                "model": model_router.last_provider_info.get("model"),
                "agent_mode": detected_mode,
            }

        except Exception as e:
            logger.exception("Voice turn execution failed")
            self._emit("idle")
            return {"success": False, "transcript": "", "reply": "",
                    "error": str(e), "latency_ms": int((time.monotonic() - start) * 1000)}
