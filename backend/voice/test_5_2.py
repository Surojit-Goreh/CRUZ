import asyncio
from .voice_manager import VoiceManager

async def main():
    vm = VoiceManager(stt_model="base.en")

    input("Press ENTER to start recording (5 seconds)...")
    result = await vm.run_turn(duration_seconds=5, save_debug_audio=True)

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