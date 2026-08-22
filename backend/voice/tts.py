import re
import base64
import io
import threading
import torch
import numpy as np
import scipy.io.wavfile as wavfile
import httpx
from kokoro import KPipeline

from config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_TTS_MODEL,
    GEMINI_TTS_VOICE,
    VOICE_MODE,
)
from utils.logger import get_logger

logger = get_logger("voice.tts")

# Optimize PyTorch CPU Threading for AMD Ryzen CPU
try:
    torch.set_num_threads(4)
except Exception:
    pass


def _clean_text_for_speech(text: str) -> str:
    """Cleans text by stripping markdown code blocks, links, and formatting before audio synthesis."""
    if not text:
        return ""
    # Strip markdown code blocks ```...```
    clean = re.sub(r'```[\s\S]*?```', ' I have provided the code in the chat. ', text)
    # Strip markdown links [text](url) -> text
    clean = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean)
    # Strip markdown asterisks, hashtags, bold
    clean = re.sub(r'[*#_`~]', '', clean)
    # Strip raw URLs
    clean = re.sub(r'https?://\S+', '', clean)
    # Collapse multiple whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean or text


def audio_to_wav_bytes(audio_array: np.ndarray, sample_rate: int = 24000) -> bytes:
    """Converts a float32 or int16 numpy audio array to 16-bit PCM WAV bytes."""
    if audio_array is None or len(audio_array) == 0:
        return b""
    if audio_array.dtype in (np.float32, np.float64):
        int_audio = np.clip(audio_array * 32767.0, -32768, 32767).astype(np.int16)
    else:
        int_audio = audio_array.astype(np.int16)

    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, int_audio)
    return buf.getvalue()


def audio_to_base64_wav(audio_array: np.ndarray, sample_rate: int = 24000) -> str:
    """Converts a float32 or int16 numpy audio array to a base64-encoded WAV string."""
    wav_bytes = audio_to_wav_bytes(audio_array, sample_rate)
    if not wav_bytes:
        return ""
    return base64.b64encode(wav_bytes).decode("utf-8")



class TextToSpeech:
    """
    Text-to-Speech synthesizer with dual engine support:
    - Online: Google AI Studio Gemini Audio Generation (high quality, natural voices)
    - Offline: Local Kokoro TTS (fast, neural 24kHz audio, 100% offline, pre-warmed)
    """

    FALLBACK_MODELS = [
        "gemini-2.5-flash-preview-tts",
        "gemini-3.1-flash-tts-preview",
    ]

    def __init__(
        self,
        voice: str = "af_heart",
        lang_code: str = "a",
        voice_mode: str = VOICE_MODE,
        gemini_api_key: str = GEMINI_API_KEY,
        gemini_model: str = GEMINI_TTS_MODEL,
        gemini_voice: str = GEMINI_TTS_VOICE,
        gemini_base_url: str = GEMINI_BASE_URL,
    ):
        self.voice = voice
        self.lang_code = lang_code
        self.voice_mode = (voice_mode or "auto").lower()
        self.gemini_api_key = gemini_api_key or ""
        self.gemini_model = gemini_model or "gemini-2.5-flash-preview-tts"
        self.gemini_voice = gemini_voice or "Puck"
        self.gemini_base_url = gemini_base_url.rstrip("/")
        self.pipeline = None
        self._init_lock = threading.Lock()

        # Pre-warm local Kokoro pipeline and JIT compiler in background daemon thread
        threading.Thread(target=self._ensure_local_pipeline, daemon=True).start()

    def _ensure_local_pipeline(self):
        """Thread-safe initialization and JIT pre-warm of local Kokoro pipeline."""
        if self.pipeline is None:
            with self._init_lock:
                if self.pipeline is None:
                    try:
                        print(f"Loading local Kokoro TTS (voice={self.voice})...")
                        p = KPipeline(lang_code=self.lang_code)
                        list(p("Ready.", voice=self.voice))
                        self.pipeline = p
                        print("Local Kokoro loaded and pre-warmed.")
                    except Exception as e:
                        logger.error(f"Kokoro initialization error: {e}")

    def _synthesize_online_gemini(self, text: str) -> tuple[np.ndarray, int]:
        """Synthesizes speech using Google AI Studio Gemini Audio generation with fast 3.0s timeout."""
        candidate_models = list(dict.fromkeys([self.gemini_model] + self.FALLBACK_MODELS))
        last_exception = None

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"Read the following text aloud with natural, clear pacing and tone without adding any other commentary:\n\n{text}"
                        }
                    ],
                }
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": self.gemini_voice
                        }
                    }
                },
            },
        }

        with httpx.Client(timeout=3.0) as client:
            for model_name in candidate_models:
                url = f"{self.gemini_base_url}/models/{model_name}:generateContent?key={self.gemini_api_key}"
                try:
                    response = client.post(url, json=payload)
                    if response.status_code == 429:
                        logger.warning(f"Gemini TTS model {model_name} rate-limited (429). Falling back to local Kokoro.")
                        break

                    response.raise_for_status()
                    data = response.json()

                    candidates = data.get("candidates", [])
                    if not candidates:
                        continue

                    parts = candidates[0].get("content", {}).get("parts", [])
                    raw_audio_bytes = None
                    mime_type = "audio/pcm;rate=24000"

                    for part in parts:
                        inline_data = part.get("inlineData") or part.get("inline_data")
                        if inline_data and "data" in inline_data:
                            raw_audio_bytes = base64.b64decode(inline_data["data"])
                            mime_type = inline_data.get("mimeType") or inline_data.get("mime_type", "")
                            break

                    if not raw_audio_bytes:
                        continue

                    # Case 1: Standard WAV format
                    if raw_audio_bytes.startswith(b"RIFF") or "wav" in mime_type.lower():
                        try:
                            sr, audio = wavfile.read(io.BytesIO(raw_audio_bytes))
                            if audio.dtype == np.int16:
                                audio_float = audio.astype(np.float32) / 32768.0
                            elif audio.dtype == np.int32:
                                audio_float = audio.astype(np.float32) / 2147483648.0
                            else:
                                audio_float = audio.astype(np.float32)
                            if audio_float.ndim > 1:
                                audio_float = audio_float.mean(axis=1)
                            logger.info(f"TTS synthesized via Google Gemini model: {model_name}")
                            return audio_float, int(sr)
                        except Exception:
                            pass

                    # Case 2: Raw PCM 16-bit little-endian (Gemini audio default)
                    sample_rate = 24000
                    if "rate=" in mime_type:
                        try:
                            sample_rate = int(mime_type.split("rate=")[1].split(";")[0])
                        except Exception:
                            sample_rate = 24000

                    pcm_int16 = np.frombuffer(raw_audio_bytes, dtype=np.int16)
                    audio_float = pcm_int16.astype(np.float32) / 32768.0
                    logger.info(f"TTS synthesized via Google Gemini model: {model_name}")
                    return audio_float, sample_rate

                except Exception as exc:
                    last_exception = exc
                    logger.debug(f"Gemini TTS model {model_name} failed/timed out: {exc}")
                    break

        if last_exception:
            raise last_exception
        return np.array([], dtype=np.float32), 24000

    def _synthesize_local(self, text: str) -> tuple[np.ndarray, int]:
        """Synthesizes speech using pre-warmed local Kokoro KPipeline."""
        self._ensure_local_pipeline()
        speech_text = _clean_text_for_speech(text)
        chunks = []
        for _, _, audio in self.pipeline(speech_text, voice=self.voice):
            chunks.append(audio)
        if not chunks:
            return np.array([], dtype=np.float32), 24000
        return np.concatenate(chunks).astype(np.float32), 24000

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        """
        Synthesizes text into audio waveform.
        Attempts Google AI Studio Gemini TTS when online and configured;
        automatically falls back to pre-warmed local Kokoro TTS when offline or rate-limited.
        Returns: (audio_array: np.ndarray, sample_rate: int)
        """
        if not text or not text.strip():
            return np.array([], dtype=np.float32), 24000

        speech_text = _clean_text_for_speech(text)

        # Attempt online Google AI Studio Gemini TTS if mode allows and API key exists
        if self.voice_mode in ("auto", "cloud") and self.gemini_api_key:
            try:
                audio, sample_rate = self._synthesize_online_gemini(speech_text)
                if audio is not None and len(audio) > 0:
                    return audio, sample_rate
            except Exception as e:
                logger.warning(f"Google AI Studio TTS unavailable/timed out ({e}). Using pre-warmed local Kokoro.")
                if self.voice_mode == "cloud":
                    raise

        # Fast Local Kokoro execution
        return self._synthesize_local(speech_text)

    def synthesize_kokoro(self, text: str) -> tuple[np.ndarray, int]:
        """
        Directly synthesizes speech using local Kokoro TTS pipeline (neural, 24kHz).
        Used for immediate sentence-by-sentence streaming TTS.
        """
        if not text or not text.strip():
            return np.array([], dtype=np.float32), 24000
        speech_text = _clean_text_for_speech(text)
        return self._synthesize_local(speech_text)

    def synthesize_sentence(self, text: str, force_kokoro: bool = True) -> tuple[np.ndarray, int]:
        """
        Synthesizes a single sentence chunk for low-latency streaming TTS.
        Defaults to local Kokoro TTS for instantaneous sub-100ms response.
        """
        if force_kokoro or self.voice_mode == "local":
            return self.synthesize_kokoro(text)
        return self.synthesize(text)