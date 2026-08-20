import asyncio
import re
import httpx
from typing import Dict, Any, Optional

from config import FIRECRAWL_API_KEY, FIRECRAWL_BASE_URL
from utils.logger import get_logger

logger = get_logger("services.firecrawl")


class FirecrawlService:
    """
    Firecrawl Clean Web Scraping & Content Extraction service.
    Converts web pages and documentation directly into AI-friendly Markdown.
    Includes smart fallback to Playwright (BrowserManager) if no API key is provided
    or if the Firecrawl endpoint is unreachable.
    """

    def __init__(self):
        self.api_key = FIRECRAWL_API_KEY
        self.base_url = FIRECRAWL_BASE_URL.rstrip("/")

    async def scrape_page(self, url: str) -> Dict[str, Any]:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        if self.api_key:
            try:
                logger.info(f"Scraping page via Firecrawl API: {url}")
                endpoint = f"{self.base_url}/v1/scrape"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "url": url,
                    "formats": ["markdown"],
                }

                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("success"):
                        doc_data = data.get("data", {})
                        markdown = doc_data.get("markdown", "")
                        meta = doc_data.get("metadata", {})
                        return {
                            "success": True,
                            "url": url,
                            "title": meta.get("title", ""),
                            "content": markdown,
                            "provider": "firecrawl",
                        }
            except Exception as e:
                logger.warning(
                    f"Firecrawl API scrape failed ({e}). Falling back to standalone HTTP fetch."
                )

        # Fallback: plain HTTP GET + basic text extraction. Deliberately
        # NOT routed through browser_manager here — that's a single shared
        # persistent browser tab, and stealing it mid-navigation for a
        # scrape would yank it away from whatever page a concurrent
        # open_url/click/type_text tool call is actively working with.
        # This path can't render JS-heavy pages, but for read-only text
        # extraction that's an acceptable tradeoff for not corrupting
        # concurrent browser state.
        logger.info(f"Extracting page content via standalone HTTP fetch: {url}")
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                html = response.text

            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""

            text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 8000:
                text = text[:8000] + "\n\n[Truncated to first 8000 characters]"

            return {
                "success": True,
                "url": url,
                "title": title,
                "content": text,
                "provider": "http_fallback",
            }
        except Exception as e:
            return {"success": False, "error": f"Standalone fetch of '{url}' failed: {e}"}

    async def crawl_site(
        self, url: str, limit: int = 5, poll_interval: float = 2.0, max_wait: float = 90.0
    ) -> Dict[str, Any]:
        if self.api_key:
            try:
                logger.info(f"Crawling site via Firecrawl API: {url} (limit={limit})")
                endpoint = f"{self.base_url}/v1/crawl"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "url": url,
                    "limit": limit,
                    "scrapeOptions": {"formats": ["markdown"]},
                }

                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    response.raise_for_status()
                    job = response.json()

                    job_id = job.get("id")
                    status_url = job.get("url")  # Firecrawl includes the poll URL directly
                    if not job_id and not status_url:
                        # Nothing to poll — return what we got rather than pretending it worked
                        return job

                    poll_url = status_url or f"{self.base_url}/v1/crawl/{job_id}"

                    elapsed = 0.0
                    while elapsed < max_wait:
                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval

                        poll_resp = await client.get(poll_url, headers=headers)
                        poll_resp.raise_for_status()
                        result = poll_resp.json()

                        status = result.get("status")
                        if status == "completed":
                            pages = result.get("data", [])
                            combined_markdown = "\n\n---\n\n".join(
                                p.get("markdown", "") for p in pages if p.get("markdown")
                            )
                            return {
                                "success": True,
                                "url": url,
                                "pages_crawled": len(pages),
                                "content": combined_markdown,
                                "provider": "firecrawl",
                            }
                        if status in ("failed", "cancelled"):
                            logger.warning(f"Firecrawl crawl job ended with status={status}: {result}")
                            break
                        # status is "scraping" or similar — keep polling

                    logger.warning(f"Firecrawl crawl job did not complete within {max_wait}s, falling back")
            except Exception as e:
                logger.warning(f"Firecrawl API crawl failed ({e}).")

        # Fallback single-page scrape via Playwright
        return await self.scrape_page(url)


firecrawl_service = FirecrawlService()