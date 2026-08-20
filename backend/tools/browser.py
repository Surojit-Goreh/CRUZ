"""
Browser automation tools interfacing with BrowserManager.
All functions are async and return JSON-serializable dicts.
"""
from typing import Optional
from services.browser_manager import browser_manager


async def open_url(url: str) -> dict:
    return await browser_manager.open_url(url)


async def search_web(query: str, engine: Optional[str] = None) -> dict:
    return await browser_manager.search_web(query, engine)


async def read_page(max_chars: int = 8000) -> dict:
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
