"""
File & folder operations tool.

Every function here is confined to CRUZ's workspace sandbox
(utils/paths.WORKSPACE_ROOT) via utils/validators.safe_path — paths
passed in are always relative to that folder, never absolute, never
allowed to escape it with '..'.

Each function returns a plain JSON-serializable dict so it can be sent
straight back to the LLM as a tool result.
"""
import shutil
import zipfile
from pathlib import Path

from utils.paths import WORKSPACE_ROOT
from utils.validators import (
    safe_path,
    ensure_extension_allowed,
    ensure_within_size_limit,
)
from utils.logger import get_logger

logger = get_logger("tools.files")


def _describe(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path.relative_to(WORKSPACE_ROOT)),
        "type": "folder" if path.is_dir() else "file",
        "size_bytes": stat.st_size if path.is_file() else None,
        "modified": stat.st_mtime,
    }


def list_directory(path: str = ".") -> dict:
    target = safe_path(path)
    if not target.exists():
        return {"success": False, "error": f"'{path}' does not exist."}
    if not target.is_dir():
        return {"success": False, "error": f"'{path}' is not a folder."}

    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    return {
        "success": True,
        "path": str(target.relative_to(WORKSPACE_ROOT)) or ".",
        "entries": [_describe(p) for p in entries],
    }


def read_file(path: str) -> dict:
    target = safe_path(path)
    if not target.exists() or not target.is_file():
        return {"success": False, "error": f"'{path}' is not a file that exists."}

    ensure_within_size_limit(target.stat().st_size)

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"success": False, "error": f"'{path}' isn't a text file CRUZ can read."}

    return {"success": True, "path": path, "content": content}


def write_file(path: str, content: str, overwrite: bool = True) -> dict:
    target = safe_path(path)
    ensure_extension_allowed(target)
    ensure_within_size_limit(len(content.encode("utf-8")))

    if target.exists() and not overwrite:
        return {"success": False, "error": f"'{path}' already exists and overwrite=False."}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    logger.info(f"wrote {target}")
    return {"success": True, "path": path, "bytes_written": len(content.encode("utf-8"))}


def create_folder(path: str) -> dict:
    target = safe_path(path)
    if target.exists():
        return {"success": False, "error": f"'{path}' already exists."}

    target.mkdir(parents=True)
    logger.info(f"created folder {target}")
    return {"success": True, "path": path}


def delete_path(path: str) -> dict:
    target = safe_path(path)
    if target == WORKSPACE_ROOT:
        return {"success": False, "error": "Refusing to delete the workspace root itself."}
    if not target.exists():
        return {"success": False, "error": f"'{path}' does not exist."}

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    logger.info(f"deleted {target}")
    return {"success": True, "path": path}


def rename_path(path: str, new_name: str) -> dict:
    target = safe_path(path)
    if not target.exists():
        return {"success": False, "error": f"'{path}' does not exist."}
    if "/" in new_name or "\\" in new_name:
        return {"success": False, "error": "new_name must be a plain name, not a path."}

    destination = target.parent / new_name
    if destination.exists():
        return {"success": False, "error": f"'{new_name}' already exists."}

    target.rename(destination)
    logger.info(f"renamed {target} -> {destination}")
    return {"success": True, "path": str(destination.relative_to(WORKSPACE_ROOT))}


def copy_path(source: str, destination: str) -> dict:
    src = safe_path(source)
    dst = safe_path(destination)

    if not src.exists():
        return {"success": False, "error": f"'{source}' does not exist."}
    if dst.exists():
        return {"success": False, "error": f"'{destination}' already exists."}

    dst.parent.mkdir(parents=True, exist_ok=True)

    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        ensure_within_size_limit(src.stat().st_size)
        shutil.copy2(src, dst)

    logger.info(f"copied {src} -> {dst}")
    return {"success": True, "path": destination}


def move_path(source: str, destination: str) -> dict:
    src = safe_path(source)
    dst = safe_path(destination)

    if not src.exists():
        return {"success": False, "error": f"'{source}' does not exist."}
    if dst.exists():
        return {"success": False, "error": f"'{destination}' already exists."}

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    logger.info(f"moved {src} -> {dst}")
    return {"success": True, "path": destination}


def search_files(query: str, path: str = ".") -> dict:
    target = safe_path(path)
    if not target.exists() or not target.is_dir():
        return {"success": False, "error": f"'{path}' is not a folder that exists."}

    query_lower = query.lower()
    matches = [
        _describe(p) for p in target.rglob("*")
        if query_lower in p.name.lower()
    ]
    # Capped so a broad search can't blow up the LLM's context window.
    return {"success": True, "query": query, "matches": matches[:200]}


def zip_path(source: str, zip_name: str) -> dict:
    src = safe_path(source)
    if not src.exists():
        return {"success": False, "error": f"'{source}' does not exist."}

    if not zip_name.lower().endswith(".zip"):
        zip_name += ".zip"
    dst = safe_path(zip_name)

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
        if src.is_file():
            zf.write(src, arcname=src.name)
        else:
            for file in src.rglob("*"):
                if file.is_file():
                    zf.write(file, arcname=file.relative_to(src.parent))

    logger.info(f"zipped {src} -> {dst}")
    return {"success": True, "path": zip_name}


def extract_zip(zip_name: str, destination: str = ".") -> dict:
    src = safe_path(zip_name)
    dst = safe_path(destination)

    if not src.exists() or src.suffix.lower() != ".zip":
        return {"success": False, "error": f"'{zip_name}' is not a .zip file that exists."}

    dst.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(src, "r") as zf:
        # Zip-slip guard: reject any entry whose extracted path would
        # land outside the destination folder.
        resolved_dst = dst.resolve()
        for member in zf.namelist():
            member_path = (dst / member).resolve()
            if not str(member_path).startswith(str(resolved_dst)):
                return {"success": False, "error": f"Unsafe entry in zip: '{member}'."}
        zf.extractall(dst)

    logger.info(f"extracted {src} -> {dst}")
    return {"success": True, "path": destination}
