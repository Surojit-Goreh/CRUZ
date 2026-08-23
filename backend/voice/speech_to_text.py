import base64
import io
import os
import re
import time
import threading
from typing import Optional, Tuple, Dict, Any
import numpy as np
import scipy.io.wavfile as wavfile
import httpx

from config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_STT_MODEL,
    GROQ_API_KEY,
    GROQ_STT_MODEL,
    OPENAI_API_KEY,
    OPENAI_STT_MODEL,
    STT_PROVIDER,
    WHISPER_MODEL,
    WHISPER_THREADS,
    VOICE_MODE,
)
from utils.logger import get_logger

logger = get_logger("voice.stt")

# Common Whisper hallucinations on silence or background noise
HALLUCINATION_PATTERNS = [
    r"^\[.*?\]$",
    r"^\(.*?\)$",
    r"thank you for watching.*",
    r"thanks for watching.*",
    r"please subscribe.*",
    r"subtitles by.*",
    r"translated by.*",
    r"community\.org.*",
    r"^you$",
    r"^thank you\.?$",
    r"^bye\.?$",
    r"^silence\.?$",
]


def clean_whisper_transcript(text: str) -> str:
    """Filters out common Whisper hallucination artifacts on background noise/silence."""
    if not text:
        return ""
    cleaned = text.strip()
    lowered = cleaned.lower()

    for pattern in HALLUCINATION_PATTERNS:
        if re.search(pattern, lowered, re.IGNORECASE):
            logger.debug(f"Filtered out hallucinated STT artifact: '{cleaned}'")
            return ""

    return cleaned


class SpeechToText:
    """
    High-Speed Multi-Model Speech-to-Text Transcriber with Collaborative Cascade:
    - Tier 1 (Ultra-Fast Cloud ~100-200ms): Groq Whisper LPU (`whisper-large-v3` / `distil-whisper-large-v3-en`)
    - Tier 2 (Multimodal Cloud ~250-400ms): Google AI Studio Gemini (`gemini-2.5-flash`, `gemini-2.0-flash`)
    - Tier 3 (Cloud Backup): OpenAI Whisper API (`whisper-1`)
    - Tier 4 (100% Offline & Private Fallback): Pre-warmed local `pywhispercpp` with multi-threading
    """

    GEMINI_FALLBACK_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    def __init__(
        self,
        model_name: str = WHISPER_MODEL,
        voice_mode: str = VOICE_MODE,
        stt_provider: str = STT_PROVIDER,
        groq_api_key: str = GROQ_API_KEY,
        groq_model: str = GROQ_STT_MODEL,
        gemini_api_key: str = GEMINI_API_KEY,
        gemini_model: str = GEMINI_STT_MODEL,
        gemini_base_url: str = GEMINI_BASE_URL,
        openai_api_key: str = OPENAI_API_KEY,
        openai_model: str = OPENAI_STT_MODEL,
        threads: int = WHISPER_THREADS,
    ):
        self.model_name = model_name
        self.voice_mode = (voice_mode or "auto").lower()
        self.stt_provider = (stt_provider or "auto").lower()

        self.groq_api_key = groq_api_key or ""
        self.groq_model = groq_model or "whisper-large-v3"

        self.gemini_api_key = gemini_api_key or ""
        self.gemini_model = gemini_model or "gemini-2.5-flash"
        self.gemini_base_url = gemini_base_url.rstrip("/")

        self.openai_api_key = openai_api_key or ""
        self.openai_model = openai_model or "whisper-1"

        self.threads = threads
        self.model = None
        self._init_lock = threading.Lock()
        self.last_stt_info: Dict[str, Any] = {}

        # Refresh provider credentials dynamically from database if available
        self._sync_dynamic_keys()

        # Pre-warm local Whisper model in background daemon thread
        threading.Thread(target=self._ensure_local_model, daemon=True).start()

    def _sync_dynamic_keys(self):
        """Fetches active keys from ProviderManager database if not set in environment."""
        try:
            from services.providers.manager import ProviderManager
            pm = ProviderManager()
            connected = pm.get_connected_providers()
            if not self.groq_api_key and "groq" in connected:
                self.groq_api_key = connected["groq"].get("api_key", "")
            if not self.gemini_api_key and "gemini" in connected:
                self.gemini_api_key = connected["gemini"].get("api_key", "")
            if not self.openai_api_key and "openai" in connected:
                self.openai_api_key = connected["openai"].get("api_key", "")
        except Exception:
            pass

    def _ensure_local_model(self):
        """Thread-safe initialization and buffer pre-warming of local Whisper model."""
        if self.model is None:
            with self._init_lock:
                if self.model is None:
                    try:
                        from pywhispercpp.model import Model
                        logger.info(f"Loading local Whisper model: '{self.model_name}' ({self.threads} threads)...")
                        m = Model(self.model_name, n_threads=self.threads)
                        # Pre-warm compute buffer with a dummy audio buffer
                        m.transcribe(np.zeros(16000, dtype=np.float32))
                        self.model = m
                        logger.info(f"Local Whisper model '{self.model_name}' loaded & pre-warmed successfully.")
                    except Exception as e:
                        logger.error(f"Whisper local initialization error: {e}")

    def _audio_to_wav_bytes(self, audio_array: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Converts a numpy audio array into standard 16-bit PCM WAV bytes."""
        if audio_array.dtype in (np.float32, np.float64):
            # Normalize to avoid clipping
            max_val = np.max(np.abs(audio_array))
            if max_val > 1.0:
                audio_array = audio_array / max_val
            int_audio = np.clip(audio_array * 32767.0, -32768, 32767).astype(np.int16)
        else:
            int_audio = audio_array.astype(np.int16)

        buf = io.BytesIO()
        wavfile.write(buf, sample_rate, int_audio)
        return buf.getvalue()

    def _transcribe_groq(self, wav_bytes: bytes) -> str:
        """
        Transcribes audio using Groq's ultra-fast LPU inference (sub-200ms).
        Model: whisper-large-v3 / distil-whisper-large-v3-en.
        """
        if not self.groq_api_key:
            return ""

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key.strip()}",
        }
        files = {
            "file": ("speech.wav", wav_bytes, "audio/wav"),
        }
        data = {
            "model": self.groq_model,
            "temperature": "0.0",
            "response_format": "json",
        }

        with httpx.Client(timeout=2.0) as client:
            response = client.post(url, headers=headers, files=files, data=data)
            if response.status_code == 429:
                logger.warning(f"Groq STT rate-limited (429). Falling back to next engine.")
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)

            response.raise_for_status()
            res_json = response.json()
            transcript = res_json.get("text", "").strip()
            return clean_whisper_transcript(transcript)

    def _transcribe_online_gemini(self, wav_bytes: bytes) -> str:
        """
        Sends audio to Google AI Studio Gemini API with fast 2.5s timeout.
        Model: gemini-2.5-flash / gemini-2.0-flash.
        """
        if not self.gemini_api_key:
            return ""

        b64_audio = base64.b64encode(wav_bytes).decode("utf-8")
        candidate_models = list(dict.fromkeys([self.gemini_model] + self.GEMINI_FALLBACK_MODELS))
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
                url = f"{self.gemini_base_url}/models/{model_name}:generateContent?key={self.gemini_api_key.strip()}"
                try:
                    response = client.post(url, json=payload)
                    if response.status_code == 429:
                        logger.warning(f"Gemini STT model {model_name} rate-limited (429). Trying fallback.")
                        continue

                    response.raise_for_status()
                    data = response.json()

                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        transcription = "".join(p.get("text", "") for p in parts).strip()
                        if transcription:
                            return transcription
                except Exception as exc:
                    last_exception = exc
                    logger.debug(f"Gemini STT model {model_name} failed: {exc}")
                    continue

        if last_exception:
            raise last_exception
        return ""

    def _transcribe_openai(self, wav_bytes: bytes) -> str:
        """
        Transcribes audio using OpenAI's Whisper API endpoint.
        Model: whisper-1.
        """
        if not self.openai_api_key:
            return ""

        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key.strip()}",
        }
        files = {
            "file": ("speech.wav", wav_bytes, "audio/wav"),
        }
        data = {
            "model": self.openai_model,
            "temperature": "0.0",
            "response_format": "json",
        }

        with httpx.Client(timeout=3.0) as client:
            response = client.post(url, headers=headers, files=files, data=data)
            if response.status_code == 429:
                logger.warning(f"OpenAI STT rate-limited (429). Falling back to local Whisper.")
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)

            response.raise_for_status()
            res_json = response.json()
            transcript = res_json.get("text", "").strip()
            return clean_whisper_transcript(transcript)

    def _transcribe_local(self, audio_array: np.ndarray) -> str:
        """
        Transcribes audio using pre-warmed local pywhispercpp multi-threaded model.
        100% offline & private fallback.
        """
        self._ensure_local_model()
        if self.model is None:
            logger.error("Local Whisper model not initialized.")
            return ""

        segments = self.model.transcribe(audio_array)
        raw_transcript = " ".join(seg.text for seg in segments).strip()
        return clean_whisper_transcript(raw_transcript)

    def transcribe_with_info(self, audio_array: np.ndarray) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribes speech audio with full collaborative multi-engine cascade.
        Returns: (transcription_text, metadata_dict)
        """
        if audio_array is None or len(audio_array) == 0:
            return "", {"provider": "none", "model": "none", "latency_ms": 0}

        # Dynamically refresh keys in case they were added in the UI
        self._sync_dynamic_keys()

        start_time = time.monotonic()
        wav_bytes = None

        def get_wav():
            nonlocal wav_bytes
            if wav_bytes is None:
                wav_bytes = self._audio_to_wav_bytes(audio_array, sample_rate=16000)
            return wav_bytes

        # If forced to local mode, bypass cloud entirely
        if self.voice_mode == "local" or self.stt_provider == "local":
            logger.info("Transcribing via Local Whisper (local mode configured)...")
            t0 = time.monotonic()
            transcript = self._transcribe_local(audio_array)
            latency = int((time.monotonic() - t0) * 1000)
            info = {"provider": "local", "model": self.model_name, "latency_ms": latency}
            self.last_stt_info = info
            logger.info(f"Local Whisper transcribed in {latency}ms: \"{transcript}\"")
            return transcript, info

        # --- Cloud Cascade ---
        # 1. Groq Whisper (LPU sub-200ms)
        if self.stt_provider in ("auto", "groq") and self.groq_api_key:
            try:
                t0 = time.monotonic()
                transcript = self._transcribe_groq(get_wav())
                if transcript:
                    latency = int((time.monotonic() - t0) * 1000)
                    info = {"provider": "groq", "model": self.groq_model, "latency_ms": latency}
                    self.last_stt_info = info
                    logger.info(f"STT transcribed via Groq ({self.groq_model}) in {latency}ms: \"{transcript}\"")
                    return transcript, info
            except Exception as e:
                logger.warning(f"Groq STT failed/unavailable ({e}). Cascading to next engine.")
                if self.stt_provider == "groq" and self.voice_mode == "cloud":
                    raise

        # 2. Google Gemini Flash (Multimodal Audio ~300ms)
        if self.stt_provider in ("auto", "gemini") and self.gemini_api_key:
            try:
                t0 = time.monotonic()
                transcript = self._transcribe_online_gemini(get_wav())
                if transcript:
                    latency = int((time.monotonic() - t0) * 1000)
                    info = {"provider": "gemini", "model": self.gemini_model, "latency_ms": latency}
                    self.last_stt_info = info
                    logger.info(f"STT transcribed via Google Gemini ({self.gemini_model}) in {latency}ms: \"{transcript}\"")
                    return transcript, info
            except Exception as e:
                logger.warning(f"Google Gemini STT failed/unavailable ({e}). Cascading to next engine.")
                if self.stt_provider == "gemini" and self.voice_mode == "cloud":
                    raise

        # 3. OpenAI Whisper (Backup Cloud)
        if self.stt_provider in ("auto", "openai") and self.openai_api_key:
            try:
                t0 = time.monotonic()
                transcript = self._transcribe_openai(get_wav())
                if transcript:
                    latency = int((time.monotonic() - t0) * 1000)
                    info = {"provider": "openai", "model": self.openai_model, "latency_ms": latency}
                    self.last_stt_info = info
                    logger.info(f"STT transcribed via OpenAI ({self.openai_model}) in {latency}ms: \"{transcript}\"")
                    return transcript, info
            except Exception as e:
                logger.warning(f"OpenAI STT failed/unavailable ({e}). Falling back to local Whisper.")
                if self.stt_provider == "openai" and self.voice_mode == "cloud":
                    raise

        # If user explicitly requested cloud-only mode and all cloud models failed
        if self.voice_mode == "cloud":
            raise RuntimeError("All configured cloud STT providers failed or unavailable.")

        # --- Tier 4: Offline Local Whisper Fallback ---
        t0 = time.monotonic()
        transcript = self._transcribe_local(audio_array)
        latency = int((time.monotonic() - t0) * 1000)
        info = {"provider": "local_fallback", "model": self.model_name, "latency_ms": latency}
        self.last_stt_info = info
        logger.info(f"STT fallback via Local Whisper ({self.model_name}) in {latency}ms: \"{transcript}\"")
        return transcript, info

    def transcribe(self, audio_array: np.ndarray) -> str:
        """Convenience method returning just the verbatim transcript text."""
        transcript, _ = self.transcribe_with_info(audio_array)
        return transcript