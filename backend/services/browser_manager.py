import os
import re
import asyncio
import time
import concurrent.futures
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.sync_api import sync_playwright, Playwright, BrowserContext, Page
from config import (
    BROWSER_PROFILE_DIR,
    BROWSER_SCREENSHOTS_DIR,
    BROWSER_HEADLESS,
    DEFAULT_SEARCH_ENGINE,
)
from utils.logger import get_logger

logger = get_logger("services.browser_manager")


class BrowserManager:
    """
    Thread-safe, Windows-compatible BrowserManager using Playwright sync_api
    pinned to a single dedicated worker thread (ThreadPoolExecutor max_workers=1)
    to guarantee greenlet thread-affinity while providing non-blocking async execution.
    """

    _instance: Optional["BrowserManager"] = None
    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="browser_worker")

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._active_page: Optional[Page] = None

        os.makedirs(BROWSER_PROFILE_DIR, exist_ok=True)
        os.makedirs(BROWSER_SCREENSHOTS_DIR, exist_ok=True)

    @classmethod
    def get_instance(cls) -> "BrowserManager":
        if cls._instance is None:
            cls._instance = BrowserManager()
        return cls._instance

    def _sync_get_context(self) -> BrowserContext:
        if self._context is not None:
            try:
                if self._context.pages:
                    if self._active_page is None or self._active_page.is_closed():
                        self._active_page = self._context.pages[0]
                    return self._context
            except Exception:
                pass
            self._sync_close()

        if self._playwright is None:
            self._playwright = sync_playwright().start()

        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
        ]
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR),
                channel="chrome",
                headless=BROWSER_HEADLESS,
                viewport={"width": 1280, "height": 800},
                user_agent=ua,
                args=args,
            )
            logger.info(f"Launched persistent Chrome context at {BROWSER_PROFILE_DIR}")
        except Exception as e:
            logger.warning(f"Chrome channel launch failed ({e}), falling back to default Chromium")
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR),
                headless=BROWSER_HEADLESS,
                viewport={"width": 1280, "height": 800},
                user_agent=ua,
                args=args,
            )
            logger.info(f"Launched persistent Chromium context at {BROWSER_PROFILE_DIR}")

        if self._context.pages:
            self._active_page = self._context.pages[0]
        else:
            self._active_page = self._context.new_page()

        return self._context

    def _sync_get_active_page(self) -> Page:
        self._sync_get_context()
        if self._active_page is None or self._active_page.is_closed():
            pages = self._context.pages if self._context else []
            if pages:
                self._active_page = pages[0]
            else:
                self._active_page = self._context.new_page()
        return self._active_page

    def _sync_open_url(self, url: str) -> Dict[str, Any]:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        page = self._sync_get_active_page()
        logger.info(f"Navigating to {url}")
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = response.status if response else 200

        return {
            "success": status < 400,
            "url": page.url,
            "title": page.title(),
            "status_code": status,
        }

    def _sync_search_web(self, query: str, engine: Optional[str] = None) -> Dict[str, Any]:
        # 1. If query contains a URL, redirect to open_url directly
        url_match = re.search(r'https?://[^\s\]\)\"]+', query)
        if url_match:
            extracted_url = url_match.group(0)
            logger.info(f"Query contains URL '{extracted_url}', redirecting search_web to open_url.")
            return self._sync_open_url(extracted_url)

        # 2. Clean query of markdown brackets or markdown link noise
        clean_query = re.sub(r'\[.*?\]|\(.*?\)', '', query).strip()
        if not clean_query:
            clean_query = query

        engine_name = (engine or DEFAULT_SEARCH_ENGINE).lower()
        q_lower = clean_query.lower()

        if "youtube" in engine_name or "youtube" in q_lower:
            search_q = q_lower.replace("youtube", "").replace("search", "").replace("for", "").strip() or clean_query
            search_url = f"https://www.youtube.com/results?search_query={search_q.replace(' ', '+')}"
        elif "duckduckgo" in engine_name:
            search_url = f"https://duckduckgo.com/?q={clean_query.replace(' ', '+')}"
        else:
            search_url = f"https://www.google.com/search?q={clean_query.replace(' ', '+')}"

        page = self._sync_get_active_page()
        logger.info(f"Navigating to search URL: {search_url}")
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_timeout(1500)
        except Exception:
            pass

        content_res = self._sync_read_page(max_chars=4000)
        return {
            "success": True,
            "url": page.url,
            "title": page.title(),
            "search_results": content_res.get("content", ""),
        }

    def _sync_read_page(self, max_chars: int = 8000) -> Dict[str, Any]:
        page = self._sync_get_active_page()

        text_content = page.evaluate("""() => {
            const clone = document.cloneNode(true);
            const scripts = clone.querySelectorAll('script, style, noscript, svg, header, footer, nav');
            scripts.forEach(s => s.remove());
            return clone.body ? (clone.body.innerText || clone.body.textContent) : '';
        }""")

        lines = [line.strip() for line in text_content.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + f"\n\n[Truncated to first {max_chars} characters]"

        return {
            "success": True,
            "url": page.url,
            "title": page.title(),
            "content": clean_text,
        }

    def _sync_click(self, target: str) -> Dict[str, Any]:
        page = self._sync_get_active_page()
        logger.info(f"Attempting to click target: '{target}'")

        try:
            locator = page.get_by_role("button", name=target)
            if locator.count() > 0:
                locator.first.click(timeout=5000)
                return {"success": True, "clicked_target": target, "method": "role_button"}

            locator = page.get_by_role("link", name=target)
            if locator.count() > 0:
                locator.first.click(timeout=5000)
                return {"success": True, "clicked_target": target, "method": "role_link"}

            locator = page.get_by_text(target)
            if locator.count() > 0:
                locator.first.click(timeout=5000)
                return {"success": True, "clicked_target": target, "method": "by_text"}

            page.click(target, timeout=5000)
            return {"success": True, "clicked_target": target, "method": "selector"}
        except Exception as e:
            return {"success": False, "error": f"Could not click target '{target}': {e}"}

    def _sync_type_text(self, target: str, text: str, press_enter: bool = True) -> Dict[str, Any]:
        page = self._sync_get_active_page()
        logger.info(f"Attempting to type into '{target}': {text}")

        def _build_result(method: str) -> Dict[str, Any]:
            # If Enter was pressed, give the page a moment to navigate/update
            # before reporting back — otherwise url/title below can still
            # reflect the pre-search state, which is exactly what made the
            # model unable to tell round 1 already worked.
            if press_enter:
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                try:
                    page.wait_for_timeout(800)
                except Exception:
                    pass
            return {
                "success": True,
                "target": target,
                "typed_text": text,
                "pressed_enter": press_enter,
                "method": method,
                "resulting_url": page.url,
                "resulting_title": page.title(),
            }

        try:
            target_lower = target.lower()
            if "search" in target_lower or "input" in target_lower or "query" in target_lower:
                for sel in ["input[name='search_query']", "input[name='q']", "input[type='search']", "input[type='text']"]:
                    if page.locator(sel).count() > 0:
                        loc = page.locator(sel).first
                        loc.fill(text, timeout=5000)
                        if press_enter:
                            loc.press("Enter", timeout=5000)
                        return _build_result(f"selector:{sel}")

            locator = page.get_by_label(target)
            if locator.count() > 0:
                locator.first.fill(text, timeout=5000)
                if press_enter:
                    locator.first.press("Enter", timeout=5000)
                return _build_result("by_label")

            locator = page.get_by_placeholder(target)
            if locator.count() > 0:
                locator.first.fill(text, timeout=5000)
                if press_enter:
                    locator.first.press("Enter", timeout=5000)
                return _build_result("by_placeholder")

            page.fill(target, text, timeout=5000)
            if press_enter:
                page.keyboard.press("Enter")
            return _build_result("raw_selector")
        except Exception as e:
            return {"success": False, "error": f"Could not type into target '{target}': {e}"}

    def _sync_take_screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        page = self._sync_get_active_page()

        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        elif not filename.endswith(".png"):
            filename += ".png"

        target_path = Path(BROWSER_SCREENSHOTS_DIR) / filename
        page.screenshot(path=str(target_path), full_page=False)
        logger.info(f"Saved screenshot to {target_path}")

        return {
            "success": True,
            "filename": filename,
            "path": str(target_path),
            "url": page.url,
        }

    def _sync_get_state(self) -> Dict[str, Any]:
        if self._context is None:
            return {"open": False, "active_tab": 0, "tabs_count": 0}

        pages = self._context.pages
        active_page = self._sync_get_active_page()

        return {
            "open": True,
            "url": active_page.url,
            "title": active_page.title(),
            "tabs_count": len(pages),
            "active_tab_index": pages.index(active_page) if active_page in pages else 0,
        }

    def _sync_close_tab(self) -> Dict[str, Any]:
        if self._active_page and not self._active_page.is_closed():
            self._active_page.close()
            pages = self._context.pages if self._context else []
            if pages:
                self._active_page = pages[-1]
            else:
                self._active_page = None
            return {"success": True, "message": "Closed active browser tab"}
        return {"success": False, "error": "No active tab to close"}

    def _sync_close(self) -> Dict[str, Any]:
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        self._active_page = None
        logger.info("Browser session closed cleanly")
        return {"success": True, "status": "closed"}

    # Async wrappers using single-threaded ThreadPoolExecutor for greenlet thread-affinity
    async def close_tab(self) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_close_tab)
    async def open_url(self, url: str) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_open_url, url)

    async def search_web(self, query: str, engine: Optional[str] = None) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_search_web, query, engine)

    async def read_page(self, max_chars: int = 8000) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_read_page, max_chars)

    async def click(self, target: str) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_click, target)

    async def type_text(self, target: str, text: str, press_enter: bool = True) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_type_text, target, text, press_enter)

    async def take_screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_take_screenshot, filename)

    async def get_state(self) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_get_state)

    async def close(self) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_close)


browser_manager = BrowserManager.get_instance()