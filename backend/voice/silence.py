import collections
import queue
import time
from typing import Optional
import numpy as np
import sounddevice as sd

from config import (
    VOICE_SILENCE_DURATION,
    VOICE_INITIAL_TIMEOUT,
    VOICE_MAX_DURATION,
)
from utils.logger import get_logger

logger = get_logger("voice.silence")


def record_until_silence(
    sample_rate: int = 16000,
    silence_duration: Optional[float] = None,
    initial_timeout: Optional[float] = None,
    max_duration: Optional[float] = None,
    min_speech_duration: float = 0.6,
    chunk_ms: int = 30,
) -> np.ndarray:
    """
    Dynamically records microphone audio until the user finishes talking.

    Features:
    - Dual-Threshold Hysteresis: High trigger threshold to start, sensitive sustain threshold to stay active.
    - Hangover Filter: Prevents micro-pauses between words from prematurely triggering silence.
    - Pre-Roll Ring Buffer: Captures 400ms prior to detected speech to preserve opening words.
    - Configurable pause duration (default 2.2s) allowing comfortable, natural conversational pauses.
    """
    silence_duration = silence_duration if silence_duration is not None else VOICE_SILENCE_DURATION
    initial_timeout = initial_timeout if initial_timeout is not None else VOICE_INITIAL_TIMEOUT
    max_duration = max_duration if max_duration is not None else VOICE_MAX_DURATION

    chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
    audio_queue: queue.Queue = queue.Queue()

    def _audio_callback(indata, frames, time_info, status):
        if status:
            logger.debug(f"Audio stream status: {status}")
        audio_queue.put(indata.copy().flatten())

    # Pre-roll ring buffer (~400ms)
    pre_roll_chunks = int(0.40 / (chunk_ms / 1000.0))
    pre_roll_buffer: collections.deque = collections.deque(maxlen=pre_roll_chunks)

    speech_frames: list[np.ndarray] = []
    speech_started = False
    speech_start_time = None
    consecutive_start_chunks = 0
    silence_start_time = None

    # Ambient noise calibration (first 300ms)
    calibration_chunks = 10
    calibration_rms_list: list[float] = []

    start_threshold = 0.008
    sustain_threshold = 0.0035

    print("[Voice] Listening... (speak whenever you're ready)")
    stream_start_time = time.monotonic()

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=chunk_samples,
        callback=_audio_callback,
    ):
        while True:
            try:
                chunk = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            now = time.monotonic()
            rms = float(np.sqrt(np.mean(chunk**2)))

            # 1. Calibration Phase (ambient background noise)
            if len(calibration_rms_list) < calibration_chunks:
                calibration_rms_list.append(rms)
                if len(calibration_rms_list) == calibration_chunks:
                    ambient_mean = float(np.mean(calibration_rms_list))
                    ambient_std = float(np.std(calibration_rms_list))
                    # Trigger threshold: clear voice above noise
                    start_threshold = max(0.007, ambient_mean + 2.5 * ambient_std + 0.003)
                    # Sustain threshold: sensitive enough to capture quiet syllables and word endings
                    sustain_threshold = max(0.003, ambient_mean + 0.8 * ambient_std + 0.001)
                    logger.debug(
                        f"Noise floor: mean={ambient_mean:.4f}, std={ambient_std:.4f} "
                        f"-> Start: {start_threshold:.4f}, Sustain: {sustain_threshold:.4f}"
                    )

            # 2. Before speech has started
            if not speech_started:
                pre_roll_buffer.append(chunk)

                if rms >= start_threshold:
                    consecutive_start_chunks += 1
                    if consecutive_start_chunks >= 2:  # ~60ms confirmation
                        speech_started = True
                        speech_start_time = now
                        logger.info("Speech detected! Recording active conversation...")
                        speech_frames.extend(list(pre_roll_buffer))
                        silence_start_time = None
                else:
                    consecutive_start_chunks = 0

                # Initial silence timeout (user never spoke)
                if now - stream_start_time >= initial_timeout:
                    logger.info(f"Initial silence timeout reached ({initial_timeout:.1f}s, no speech).")
                    break

            # 3. Active speech in progress
            else:
                speech_frames.append(chunk)
                total_spoken_time = now - (speech_start_time or now)

                if rms >= sustain_threshold:
                    # User is actively speaking — reset silence timer completely
                    silence_start_time = None
                else:
                    # Energy dropped below sustain threshold
                    # Only allow silence turn-end if min_speech_duration has elapsed
                    if total_spoken_time >= min_speech_duration:
                        if silence_start_time is None:
                            silence_start_time = now
                        elif now - silence_start_time >= silence_duration:
                            logger.info(
                                f"Silence detected ({silence_duration:.1f}s pause after speaking). "
                                f"Total speech: {total_spoken_time:.1f}s. Finalizing recording."
                            )
                            break

            # 4. Max recording duration safety limit
            if now - stream_start_time >= max_duration:
                logger.info(f"Max recording duration reached ({max_duration:.1f}s). Finalizing recording.")
                break

    if not speech_frames:
        if speech_started and pre_roll_buffer:
            return np.concatenate(list(pre_roll_buffer))
        return np.array([], dtype=np.float32)

    full_audio = np.concatenate(speech_frames).astype(np.float32)
    duration = len(full_audio) / sample_rate
    print(f"[Voice] Input captured ({duration:.1f}s).")
    return full_audio
