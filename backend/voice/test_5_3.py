import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.voice_manager import VoiceManager

async def main():
    vm = VoiceManager()

    print("=" * 50)
    print(" CRUZ Dynamic Voice Activity & Silence Detection Test")
    print("=" * 50)
    print("Cruz will now continuously record until you pause/stop talking.")
    print("Speak a short or long sentence and then stay quiet.")
    input("\nPress ENTER when you are ready to speak...")
    
    result = await vm.run_turn(duration_seconds=None, save_debug_audio=True)

    print("\n" + "=" * 50)
    if result["success"]:
        print(f"🎤 You said:\n\"{result['transcript']}\"\n")
        print(f"🤖 CRUZ replied:\n\"{result['reply']}\"")
    else:
        print(f"❌ Result: {result['error']}")
    print(f"\n⏱ Turn Latency: {result['latency_ms']}ms")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())