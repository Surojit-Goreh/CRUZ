import base64
import io
import threading
import numpy as np
import scipy.io.wavfile as wavfile
import httpx
from pywhispercpp.model import Model

from config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_STT_MODEL,
    WHISPER_MODEL,
    VOICE_MODE,
)
from utils.logger import get_logger

logger = get_logger("voice.stt")


class SpeechToText:
    """
    High-Speed Speech-to-Text transcriber with dual engine support:
    - Online: Google AI Studio Gemini API (sub-second ~0.3s transcription, multilingual)
    - Offline: Local pywhispercpp (whisper.cpp multi-threaded, 100% private offline fallback)
    """

    FALLBACK_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    def __init__(
        self,
        model_name: str = WHISPER_MODEL,
        voice_mode: str = VOICE_MODE,
        gemini_api_key: str = GEMINI_API_KEY,
        gemini_model: str = GEMINI_STT_MODEL,
        gemini_base_url: str = GEMINI_BASE_URL,
    ):
        self.model_name = model_name
        self.voice_mode = (voice_mode or "auto").lower()
        self.gemini_api_key = gemini_api_key or ""
        self.gemini_model = gemini_model or "gemini-2.5-flash"
        self.gemini_base_url = gemini_base_url.rstrip("/")
        self.model = None
        self._init_lock = threading.Lock()

        # Pre-warm local Whisper model in background daemon thread
        threading.Thread(target=self._ensure_local_model, daemon=True).start()

    def _ensure_local_model(self):
        """Thread-safe initialization and buffer pre-warming of local Whisper model."""
        if self.model is None:
            with self._init_lock:
                if self.model is None:
                    try:
                        print(f"Loading local Whisper model: {self.model_name} (8 threads)...")
                        m = Model(self.model_name, n_threads=8)
                        # Pre-warm compute buffer
                        m.transcribe(np.zeros(16000, dtype=np.float32))
                        self.model = m
                        print("Local Whisper model loaded and pre-warmed.")
                    except Exception as e:
                        logger.error(f"Whisper initialization error: {e}")

    def _audio_to_wav_bytes(self, audio_array: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Converts a numpy audio array into standard 16-bit PCM WAV bytes."""
        if audio_array.dtype in (np.float32, np.float64):
            int_audio = np.clip(audio_array * 32767.0, -32768, 32767).astype(np.int16)
        else:
            int_audio = audio_array.astype(np.int16)

        buf = io.BytesIO()
        wavfile.write(buf, sample_rate, int_audio)
        return buf.getvalue()

    def _transcribe_online_gemini(self, audio_array: np.ndarray) -> str:
        """Sends audio to Google AI Studio Gemini API with fast 2.5s timeout."""
        wav_bytes = self._audio_to_wav_bytes(audio_array, sample_rate=16000)
        b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

        candidate_models = list(dict.fromkeys([self.gemini_model] + self.FALLBACK_MODELS))
        last_exception = None

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "audio/wav",
                                "data": b64_audio,
                            }
                        },
                        {
                            "text": (
                                "Transcribe the spoken words in the audio accurately. "
                                "Output ONLY the verbatim transcription text with no additional commentary, "
                                "labels, or markdown formatting."
                            )
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
            },
        }

        with httpx.Client(timeout=2.5) as client:
            for model_name in candidate_models:
                url = f"{self.gemini_base_url}/models/{model_name}:generateContent?key={self.gemini_api_key}"
                try:
                    response = client.post(url, json=payload)
                    if response.status_code == 429:
                        logger.warning(f"Gemini STT model {model_name} rate-limited (429). Falling back to local Whisper.")
                        break

                    response.raise_for_status()
                    data = response.json()

                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        transcription = "".join(p.get("text", "") for p in parts).strip()
                        if transcription:
                            logger.info(f"STT transcribed via Google Gemini model: {model_name}")
                            return transcription
                except Exception as exc:
                    last_exception = exc
                    logger.debug(f"Gemini STT model {model_name} failed/timed out: {exc}")
                    break

        if last_exception:
            raise last_exception
        return ""

    def _transcribe_local(self, audio_array: np.ndarray) -> str:
        """Transcribes audio using pre-warmed local pywhispercpp model."""
        self._ensure_local_model()
        segments = self.model.transcribe(audio_array)
        return " ".join(seg.text for seg in segments).strip()

    def transcribe(self, audio_array: np.ndarray) -> str:
        """
        Transcribes speech audio array.
        Attempts sub-second Google AI Studio Gemini STT when online and configured;
        automatically falls back to pre-warmed local Whisper.cpp when offline or rate-limited.
        """
        if audio_array is None or len(audio_array) == 0:
            return ""

        # Attempt online Google AI Studio STT if mode allows and API key exists
        if self.voice_mode in ("auto", "cloud") and self.gemini_api_key:
            try:
                transcript = self._transcribe_online_gemini(audio_array)
                if transcript:
                    return transcript
            except Exception as e:
                logger.warning(f"Google AI Studio STT unavailable/timed out ({e}). Using local Whisper.")
                if self.voice_mode == "cloud":
                    raise

        # Fallback / Offline local execution
        return self._transcribe_local(audio_array)