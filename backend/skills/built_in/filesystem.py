from typing import List, Dict, Any, Callable, Optional
from skills.base import BaseSkill
from tools import files
from tools.schemas import FILE_TOOL_SCHEMAS


class FilesystemSkill(BaseSkill):
    name = "filesystem"
    display_name = "Filesystem & Workspace"
    description = "Read, write, create, delete, copy, move, search, and zip/unzip files and folders in the workspace sandbox."
    icon = "FolderOpen"
    version = "1.0.0"
    is_core = False
    enabled_by_default = True

    task_categories = ["coding", "general", "writing", "reasoning"]
    trigger_keywords = [
        "file", "folder", "directory", "read", "write", "create", "delete",
        "copy", "move", "rename", "zip", "extract", "save", "workspace", "path"
    ]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return FILE_TOOL_SCHEMAS

    def get_tool_registry(self) -> Dict[str, Callable]:
        return {
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
        }

    def get_prompt_instructions(self) -> Optional[str]:
        return (
            "FILESYSTEM SKILL GUIDELINES:\n"
            "- Always invoke file operations via real tool calls.\n"
            "- When asked to build apps, websites, or scripts, create all required files completely without stubs or placeholders.\n"
            "- Target existing files accurately when updating or modifying code."
        )
