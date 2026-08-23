"""
Browser automation tools interfacing with BrowserManager.
All functions are async and return JSON-serializable dicts.
"""
from typing import Optional, Union, Dict, Any
from services.browser_manager import browser_manager
from tools.web_search import search_web_instant


async def open_url(url: str) -> dict:
    return await browser_manager.open_url(url)


async def play_youtube(query: str) -> dict:
    return await browser_manager.play_youtube(query)


async def search_web(query: str, engine: Optional[str] = None) -> Union[Dict[str, Any], str]:
    q_lower = query.lower() if query else ""
    if (engine and "youtube" in engine.lower()) or ("youtube" in q_lower and any(k in q_lower for k in ("play", "song", "music", "video", "track", "listen"))):
        return await browser_manager.play_youtube(query)
    if engine and "youtube" in engine.lower():
        return await browser_manager.search_web(query, engine)
    try:
        results = search_web_instant(query)
        return {"results": results, "query": query, "fast_search": True}
    except Exception:
        return await browser_manager.search_web(query, engine)



async def read_page(max_chars: int = 8000, url: Optional[str] = None) -> dict:
    if url:
        await browser_manager.open_url(url)
    return await browser_manager.read_page(max_chars=max_chars)


async def click_element(target: str) -> dict:
    return await browser_manager.click(target)


async def type_text(target: str, text: str) -> dict:
    return await browser_manager.type_text(target, text)


async def take_screenshot(filename: Optional[str] = None) -> dict:
    return await browser_manager.take_screenshot(filename)


async def browser_status() -> dict:
    return await browser_manager.get_state()


async def close_tab() -> dict:
    return await browser_manager.close_tab()


async def close_browser() -> dict:
    return await browser_manager.close()
