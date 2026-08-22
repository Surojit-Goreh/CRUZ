"""
Tool schemas describing the file operations to the LLM, in the
OpenAI-compatible function-calling format Ollama's /api/chat accepts via
the "tools" field.
"""

FILE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders inside a directory in CRUZ's workspace. Use '.' for the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to list. Defaults to '.' (the workspace root)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the text content of a file in CRUZ's workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the file to read."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file in CRUZ's workspace with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the file to write."},
                    "content": {"type": "string", "description": "Full text content to write to the file."},
                    "overwrite": {"type": "boolean", "description": "Whether to overwrite if the file already exists. Defaults to true."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a new folder in CRUZ's workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the folder to create."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_path",
            "description": "Permanently delete a file or folder (and its contents) from CRUZ's workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the file or folder to delete."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rename_path",
            "description": "Rename a file or folder in place, without moving it to a different folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the file or folder to rename."},
                    "new_name": {"type": "string", "description": "New name only (not a path) — e.g. 'notes.txt'."},
                },
                "required": ["path", "new_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "copy_path",
            "description": "Copy a file or folder to a new location within CRUZ's workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Relative path of the file or folder to copy."},
                    "destination": {"type": "string", "description": "Relative path of where the copy should be created."},
                },
                "required": ["source", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_path",
            "description": "Move a file or folder to a new location within CRUZ's workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Relative path of the file or folder to move."},
                    "destination": {"type": "string", "description": "Relative destination path."},
                },
                "required": ["source", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files or folders whose name contains a given text, within a folder in CRUZ's workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for in file/folder names."},
                    "path": {"type": "string", "description": "Folder to search inside. Defaults to '.' (the whole workspace)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "zip_path",
            "description": "Compress a file or folder in CRUZ's workspace into a .zip archive.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Relative path of the file or folder to zip."},
                    "zip_name": {"type": "string", "description": "Name (or relative path) for the resulting .zip file."},
                },
                "required": ["source", "zip_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_zip",
            "description": "Extract a .zip archive in CRUZ's workspace into a destination folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zip_name": {"type": "string", "description": "Relative path of the .zip file to extract."},
                    "destination": {"type": "string", "description": "Folder to extract into. Defaults to '.' (the workspace root)."},
                },
                "required": ["zip_name"],
            },
        },
    },
]

BROWSER_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a website URL in CRUZ's browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL or domain to navigate to (e.g. 'https://github.com')."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search Google or YouTube for queries, topics, songs, videos, or articles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query keywords (e.g. 'python tutorial' or 'sitare song')."},
                    "engine": {"type": "string", "description": "Search engine ('google', 'youtube', or 'duckduckgo'). Defaults to google."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": "Extract readable text content from the current active browser page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_chars": {"type": "integer", "description": "Maximum characters to return. Defaults to 8000."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click_element",
            "description": "Click a button, link, or element on the current browser page by visible text or role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Visible text, button label, or link text to click (e.g. 'Sign In' or 'Search')."},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Enter text into an input field, search box, or form on the active browser page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Field label, placeholder, or selector (e.g. 'Search' or 'Username')."},
                    "text": {"type": "string", "description": "Text to enter into the field."},
                },
                "required": ["target", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture a screenshot of the current active browser page and save it to disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Optional filename (e.g. 'google_results.png')."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_status",
            "description": "Get current browser state including active URL, page title, and open tab count.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_tab",
            "description": "Close the active browser tab or page.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_browser",
            "description": "Close the browser session cleanly.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

SYSTEM_DESKTOP_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "launch_app",
              "description": "Launch an allowlisted desktop application on Windows (e.g. Notepad, Calculator, VS Code, Chrome, Spotify). Arbitrary commands and arguments are blocked.",
            "parameters": {
                "type": "object",
                "properties": {
                      "app_name": {"type": "string", "description": "Allowlisted app name (e.g. 'notepad', 'calc', 'vscode', 'chrome', 'spotify')."},
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_stats",
            "description": "Get current CPU %, RAM usage, Disk space, and Battery status.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

RESEARCH_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "scrape_page",
            "description": "Extract clean Markdown content from a web page or documentation site.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL of the page to scrape (e.g. 'https://fastapi.tiangolo.com')."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crawl_site",
            "description": "Crawl a multi-page website or documentation portal into clean Markdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Starting URL to crawl."},
                    "limit": {"type": "integer", "description": "Maximum number of pages to crawl (default 5)."},
                },
                "required": ["url"],
            },
        },
    },
]

IMAGE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate high-quality HD images from a descriptive prompt and render them directly in the chatbox. NEVER open external browser windows for images.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Detailed visual description of the image to generate."},
                    "aspect_ratio": {"type": "string", "enum": ["1:1", "16:9", "9:16", "4:3", "3:4"], "description": "Image aspect ratio. Defaults to '1:1'."},
                    "enhance": {"type": "boolean", "description": "Whether to enhance the prompt for photorealism and fine detail. Defaults to true."},
                },
                "required": ["prompt"],
            },
        },
    },
]

AGENT_CONTROL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "set_agent_mode",
            "description": "Switch CRUZ's active agent mode dynamically (e.g. when user says 'change your mode to reasoning', 'switch to image agent', 'switch to coding/build', 'switch to writer', 'switch to fast chat', or 'switch to auto').",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "build", "plan", "image", "writing", "chat"],
                        "description": "Target agent mode: 'auto' (Auto Dispatcher), 'build' (Coding), 'plan' (Reasoning), 'image' (Vision/Image), 'writing' (Writer), 'chat' (Fast Speed).",
                    },
                },
                "required": ["mode"],
            },
        },
    },
]
