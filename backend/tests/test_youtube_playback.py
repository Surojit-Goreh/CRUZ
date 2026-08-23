import os
import sys
import asyncio

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.browser import play_youtube, search_web, close_browser


async def test_youtube_flow():
    print("=" * 60)
    print(" Testing Fast One-Shot YouTube Video Playback")
    print("=" * 60)

    # 1. Test direct play_youtube tool call
    print("\n[1/2] Invoking play_youtube('believer imagine dragons')...")
    res1 = await play_youtube("believer imagine dragons")
    print(" Result 1:", res1)
    assert res1.get("success") is True, f"play_youtube failed: {res1}"
    assert "youtube.com" in res1.get("url", ""), f"Unexpected URL: {res1.get('url')}"
    print(" Direct play_youtube succeeded!")

    # 2. Test search_web auto-redirect when a play request is passed
    print("\n[2/2] Invoking search_web('play shape of you ed sheeran on youtube')...")
    res2 = await search_web("play shape of you ed sheeran on youtube")
    print(" Result 2:", res2)
    assert res2.get("success") is True, f"search_web playback failed: {res2}"
    assert "youtube.com" in res2.get("url", ""), f"Unexpected URL: {res2.get('url')}"
    print(" Search web auto-playback redirect succeeded!")

    # Clean up
    print("\nCleaning up and closing browser session...")
    await close_browser()
    print("\n" + "=" * 60)
    print(" All YouTube playback tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_youtube_flow())
