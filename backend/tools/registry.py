"""
Maps tool names (as the LLM refers to them) to the actual Python
functions that implement them, and exposes the combined schema list to
advertise to the model.
"""
from tools import files, browser, firecrawl, desktop, system
from tools.schemas import (
    FILE_TOOL_SCHEMAS,
    BROWSER_TOOL_SCHEMAS,
    SYSTEM_DESKTOP_TOOL_SCHEMAS,
    RESEARCH_TOOL_SCHEMAS,
)

TOOL_REGISTRY = {
    # File tools
    "list_directory": files.list_directory,
    "read_file": files.read_file,
    "write_file": files.write_file,
    "create_folder": files.create_folder,
    "delete_path": files.delete_path,
    "rename_path": files.rename_path,
    "copy_path": files.copy_path,
    "move_path": files.move_path,
    "search_files": files.search_files,
    "zip_path": files.zip_path,
    "extract_zip": files.extract_zip,

    # Browser tools
    "open_url": browser.open_url,
    "search_web": browser.search_web,
    "read_page": browser.read_page,
    "click_element": browser.click_element,
    "type_text": browser.type_text,
    "take_screenshot": browser.take_screenshot,
    "browser_status": browser.browser_status,
    "close_tab": browser.close_tab,
    "close_browser": browser.close_browser,

    # System & Desktop Automation tools
    "launch_app": desktop.launch_app,
    "close_app": desktop.close_app,
    "get_system_stats": system.get_system_stats,

    # Research / Firecrawl tools
    "scrape_page": firecrawl.scrape_page,
    "crawl_site": firecrawl.crawl_site,
}

ALL_TOOL_SCHEMAS = [
    *FILE_TOOL_SCHEMAS,
    *BROWSER_TOOL_SCHEMAS,
    *SYSTEM_DESKTOP_TOOL_SCHEMAS,
    *RESEARCH_TOOL_SCHEMAS,
]


def get_tool(name: str):
    return TOOL_REGISTRY.get(name)
