import asyncio
import os
import sys
import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.sentence_chunker import SentenceChunker, stream_sentences, extract_completed_sentences
from voice.tts import audio_to_base64_wav, audio_to_wav_bytes


async def test_sentence_chunking():
    print("=" * 60)
    print(" 1. Testing Sentence Chunker Logic")
    print("=" * 60)

    # Test Case 1: Simple multi-sentence text
    text = "Hello world! This is CRUZ. How can I help you today?\nI am ready."
    sentences, rem = extract_completed_sentences(text)
    print("Input:", repr(text))
    print("Extracted sentences:", sentences)
    print("Remainder:", repr(rem))
    assert len(sentences) >= 4, f"Expected at least 4 sentences, got {len(sentences)}"
    assert "Hello world!" in sentences
    assert "This is CRUZ." in sentences
    assert "How can I help you today?" in sentences
    assert "I am ready." in sentences

    # Test Case 2: Guard against decimals (e.g. 3.14)
    decimal_text = "The value of pi is 3.14 approximately. Do you need more decimals?"
    d_sentences, d_rem = extract_completed_sentences(decimal_text)
    print("\nDecimal test input:", repr(decimal_text))
    print("Extracted sentences:", d_sentences)
    assert len(d_sentences) == 2, f"Expected 2 sentences (not splitting on 3.14), got {len(d_sentences)}"
    assert "The value of pi is 3.14 approximately." == d_sentences[0]

    # Test Case 3: Token-by-token async stream
    print("\n--- Testing async stream_sentences() with streaming tokens ---")
    tokens = [
        "Hello", " there", "!", " Welcome", " to", " the", " streaming",
        " voice", " pipeline", ".", " Dr.", " Smith", " is", " testing",
        " this", " feature", "?", " Yes", ",", " it", " works", " nicely"
    ]

    async def fake_token_generator():
        for t in tokens:
            await asyncio.sleep(0.01)
            yield t

    streamed_sentences = []
    async for s in stream_sentences(fake_token_generator()):
        print(f"  -> Streamed sentence: {repr(s)}")
        streamed_sentences.append(s)

    assert len(streamed_sentences) >= 3, f"Expected >= 3 sentences, got {len(streamed_sentences)}"
    print(f"[OK] Token streaming test passed! ({len(streamed_sentences)} sentences extracted)")


def test_audio_encoding():
    print("\n" + "=" * 60)
    print(" 2. Testing Audio Base64 & WAV Encoding")
    print("=" * 60)

    # Create dummy 1-second 24kHz sine wave
    sr = 24000
    t = np.linspace(0, 1.0, sr, dtype=np.float32)
    sine_audio = 0.5 * np.sin(2 * np.pi * 440 * t)

    wav_bytes = audio_to_wav_bytes(sine_audio, sr)
    assert len(wav_bytes) > 44, "WAV bytes must have valid header and payload"
    assert wav_bytes[:4] == b"RIFF", "WAV must start with RIFF header"

    b64_audio = audio_to_base64_wav(sine_audio, sr)
    assert len(b64_audio) > 0, "Base64 string must not be empty"
    print(f"[OK] Audio encoding passed! WAV size: {len(wav_bytes)} bytes, Base64 len: {len(b64_audio)}")



async def test_full_pipeline():
    print("\n" + "=" * 60)
    print(" 3. Testing VoiceManager Streaming Pipeline Integration")
    print("=" * 60)

    from voice.voice_manager import VoiceManager

    events_received = []
    def on_event(event):
        events_received.append(event)
        if event.get("state") == "speaking":
            print(f"  [WS Event] state=speaking, idx={event.get('sentence_index')}, text={repr(event.get('text'))}, audio_len={len(event.get('audio', ''))}")

    vm = VoiceManager(on_event=on_event)

    # Mock token generator simulating fast LLM output
    sample_text_chunks = [
        "Chunking ", "the LLM stream ", "into sentences ", "is working! ",
        "Each sentence is synthesized ", "with Kokoro TTS. ",
        "Audio chunks are immediately pushed ", "over the websocket."
    ]

    async def mock_stream():
        for chunk in sample_text_chunks:
            yield chunk
            await asyncio.sleep(0.01)

    print("Streaming mock LLM tokens through VoiceManager...")
    reply = await vm.stream_reply_tts(mock_stream())

    print(f"\nFinal Accumulated Reply: {repr(reply)}")
    speaking_events = [e for e in events_received if e.get("state") == "speaking"]
    print(f"Total 'speaking' WebSocket events pushed: {len(speaking_events)}")
    assert len(speaking_events) >= 3, f"Expected at least 3 speaking events, got {len(speaking_events)}"
    for e in speaking_events:
        assert "audio" in e and len(e["audio"]) > 0, "Each speaking event must have base64 audio"
        assert "text" in e and len(e["text"]) > 0, "Each speaking event must have sentence text"

    print("\n[OK] All Streaming TTS and WebSocket tests passed successfully!")



async def main():
    await test_sentence_chunking()
    test_audio_encoding()
    await test_full_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
