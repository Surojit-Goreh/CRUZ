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
