from pywhispercpp.model import Model

class SpeechToText:
    def __init__(self, model_name="base.en"):
        print(f"Loading Whisper model: {model_name}...")
        self.model = Model(model_name, n_threads=4)
        print("Model loaded.")

    def transcribe(self, audio_array) -> str:
        segments = self.model.transcribe(audio_array)
        return " ".join(seg.text for seg in segments).strip()