from typing import List, Dict, Any, Callable, Optional
from skills.base import BaseSkill
from tools import firecrawl
from tools.schemas import RESEARCH_TOOL_SCHEMAS


class WebSearchSkill(BaseSkill):
    name = "web_search"
    display_name = "Deep Web Research"
    description = "Scrape and crawl multi-page websites into clean Markdown format using Firecrawl for deep research."
    icon = "Search"
    version = "1.0.0"
    is_core = False
    enabled_by_default = True

    task_categories = ["general", "reasoning", "coding", "writing"]
    trigger_keywords = [
        "scrape", "crawl", "documentation", "extract markdown", "docs", "research website", "firecrawl",
        "buy", "price", "compare", "best under", "review", "specs", "deals"
    ]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return RESEARCH_TOOL_SCHEMAS

    def get_tool_registry(self) -> Dict[str, Callable]:
        return {
            "scrape_page": firecrawl.scrape_page,
            "crawl_site": firecrawl.crawl_site,
        }

    def get_prompt_instructions(self) -> Optional[str]:
        return (
            "DEEP RESEARCH SKILL GUIDELINES:\n"
            "- Use 'scrape_page' to read detailed API docs or articles as Markdown.\n"
            "- Use 'crawl_site' when you need comprehensive multi-page documentation context."
        )
