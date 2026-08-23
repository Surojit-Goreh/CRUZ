from typing import List, Dict, Any, Callable, Optional
from skills.base import BaseSkill
from tools import browser
from tools.schemas import BROWSER_TOOL_SCHEMAS


class BrowserSkill(BaseSkill):
    name = "browser"
    display_name = "Browser Automation"
    description = "Control a Chromium browser with Playwright: open URLs, navigate tabs, read page content, click buttons, type input, and take screenshots."
    icon = "Globe"
    version = "1.0.0"
    is_core = False
    enabled_by_default = True

    task_categories = ["general", "coding", "reasoning"]
    trigger_keywords = [
        "browser", "browse", "website", "url", "open", "webpage", "click",
        "type", "screenshot", "tab", "navigate", "youtube", "google",
        "play", "song", "music", "video", "track", "listen", "audio"
    ]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return BROWSER_TOOL_SCHEMAS

    def get_tool_registry(self) -> Dict[str, Callable]:
        return {
            "open_url": browser.open_url,
            "play_youtube": browser.play_youtube,
            "search_web": browser.search_web,
            "read_page": browser.read_page,
            "click_element": browser.click_element,
            "type_text": browser.type_text,
            "take_screenshot": browser.take_screenshot,
            "browser_status": browser.browser_status,
            "close_tab": browser.close_tab,
            "close_browser": browser.close_browser,
        }

    def get_prompt_instructions(self) -> Optional[str]:
        return (
            "YOUTUBE & MEDIA PLAYBACK:\n"
            "- When the user asks to play a song, music, video, or audio on YouTube (e.g. 'play Shape of You', 'play Believer on YouTube', 'play lofi beats'), ALWAYS invoke 'play_youtube' with the song/video title.\n"
            "- 'play_youtube' opens YouTube, finds the best video match, and starts unmuted playback instantly in a single reliable step. NEVER call search_web + click_element in a loop for YouTube playback.\n\n"
            "WEB SEARCH & RESEARCH WORKFLOW:\n"
            "- When asked to research products (monitors, laptops, gadgets), compare prices, or find web information, ALWAYS invoke 'search_web' with descriptive keywords (e.g. 'best monitor under 10000 india amazon flipkart').\n"
            "- 'search_web' aggregates live results across multiple platforms (Amazon, Flipkart, Croma, tech review sites, official brand pages).\n"
            "- Never guess or hardcode a single store URL without searching first.\n"
            "- Provide a well-rounded multi-store comparison with prices, key specs, pros/cons, and direct product links."
        )

