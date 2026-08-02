from kokoro import KPipeline
import numpy as np

class TextToSpeech:
    def __init__(self, voice="af_heart", lang_code="a"):
        print(f"Loading Kokoro TTS (voice={voice})...")
        self.pipeline = KPipeline(lang_code=lang_code)
        self.voice = voice
        print("Kokoro loaded.")

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        """Returns (audio_array, sample_rate). Kokoro outputs at 24kHz."""
        chunks = []
        for _, _, audio in self.pipeline(text, voice=self.voice):
            chunks.append(audio)
        if not chunks:
            return np.array([]), 24000
        return np.concatenate(chunks), 24000