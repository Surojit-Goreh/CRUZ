"""
Fast Instant Web Search tool for CRUZ.
Fetches top live search results, summaries, and URLs from DuckDuckGo in <0.5s without opening a browser.
"""
import re
import urllib.parse
from html.parser import HTMLParser
from typing import List, Dict, Any
import httpx

from utils.logger import get_logger

logger = get_logger("tools.web_search")


class _DDGHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results: List[Dict[str, str]] = []
        self._current_result: Dict[str, str] = {}
        self._in_title = False
        self._in_snippet = False
        self._in_link = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")

        if tag == "a" and "result__snippet" in class_name:
            self._in_snippet = True
        elif tag == "a" and "result__url" in class_name:
            href = attrs_dict.get("href", "")
            if href and "uddg=" in href:
                # Extract actual target URL from DDG redirect
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    href = urllib.parse.unquote(m.group(1))
            self._current_result["url"] = href
        elif tag == "a" and ("result__a" in class_name or "result-link" in class_name):
            self._in_title = True
            href = attrs_dict.get("href", "")
            if href and "uddg=" in href:
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    href = urllib.parse.unquote(m.group(1))
            self._current_result["url"] = href
        elif tag == "div" and "result__snippet" in class_name:
            self._in_snippet = True

    def handle_endtag(self, tag):
        if tag == "a" or tag == "div":
            self._in_title = False
            self._in_snippet = False
            if self._current_result.get("title") and self._current_result.get("snippet"):
                self.results.append(dict(self._current_result))
                self._current_result = {}

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self._current_result["title"] = self._current_result.get("title", "") + " " + text
        elif self._in_snippet:
            self._current_result["snippet"] = self._current_result.get("snippet", "") + " " + text


def search_web_instant(query: str, max_results: int = 5) -> str:
    """
    Searches the live web for the given query and returns top snippets, titles, and URLs.
    Executes in <0.5s directly via HTTP.
    """
    clean_query = query.strip()
    if not clean_query:
        return "Error: Search query cannot be empty."

    logger.info(f"Executing fast web search for query: '{clean_query}'")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": clean_query},
                headers=headers,
            )
            if resp.status_code != 200:
                return f"Web search returned status code {resp.status_code}. Unable to fetch results."

            parser = _DDGHTMLParser()
            parser.feed(resp.text)
            results = parser.results[:max_results]

            if not results:
                # Regex fallback
                raw_snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                raw_titles = re.findall(r'<a class="result__a[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                for i in range(min(len(raw_titles), len(raw_snippets), max_results)):
                    t = re.sub(r"<[^>]+>", "", raw_titles[i]).strip()
                    s = re.sub(r"<[^>]+>", "", raw_snippets[i]).strip()
                    if t and s:
                        results.append({"title": t, "snippet": s, "url": ""})

            if not results:
                return f"No relevant web search results found for query: '{clean_query}'."

            formatted = [f"### Web Search Results for: **{clean_query}**\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "Untitled").strip()
                snippet = r.get("snippet", "").strip()
                url = r.get("url", "").strip()
                link_md = f"[{title}]({url})" if url else f"**{title}**"
                formatted.append(f"{i}. {link_md}\n   {snippet}\n")

            return "\n".join(formatted)

    except Exception as e:
        logger.warning(f"Fast web search failed: {e}")
        return f"Web search encountered an error: {e}"
