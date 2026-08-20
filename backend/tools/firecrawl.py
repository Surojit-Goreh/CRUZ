from typing import Dict, Any, Optional
from services.firecrawl import firecrawl_service


async def scrape_page(url: str) -> Dict[str, Any]:
    """
    Extract clean Markdown content from a web page or documentation site
    using Firecrawl (with automatic Playwright fallback).
    """
    return await firecrawl_service.scrape_page(url)


async def crawl_site(url: str, limit: int = 5) -> Dict[str, Any]:
    """
    Crawl a multi-page site or documentation portal into clean Markdown.
    """
    return await firecrawl_service.crawl_site(url, limit=limit)
