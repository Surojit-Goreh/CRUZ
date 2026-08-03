"""
Maps tool names (as the LLM refers to them) to the actual Python
functions that implement them, and exposes the combined schema list to
advertise to the model.

Adding a new tool category later (browser.py, desktop.py, system.py)
means: implement the functions, add their schemas to a new schemas file,
add their entries here — nothing else in the executor or llm.py needs to
change.
"""
from tools import files
from tools.schemas import FILE_TOOL_SCHEMAS

TOOL_REGISTRY = {
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

ALL_TOOL_SCHEMAS = [*FILE_TOOL_SCHEMAS]


def get_tool(name: str):
    return TOOL_REGISTRY.get(name)
