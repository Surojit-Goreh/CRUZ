import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.voice_manager import VoiceManager

async def main():
    vm = VoiceManager()

    input("Press ENTER to start speaking (Cruz will listen until you stop talking)...")
    result = await vm.run_turn(duration_seconds=None, save_debug_audio=True)

    print("\n" + "=" * 40)
    if result["success"]:
        print(f"🎤 You:\n{result['transcript']}\n")
        print(f"🤖 CRUZ:\n{result['reply']}")
    else:
        print(f"❌ Error: {result['error']}")
    print(f"\n⏱  {result['latency_ms']}ms")
    print("=" * 40)

if __name__ == "__main__":
    asyncio.run(main())