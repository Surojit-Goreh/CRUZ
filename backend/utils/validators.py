"""
Safety checks every file tool runs before touching disk.
"""
from pathlib import Path

from utils.paths import WORKSPACE_ROOT


class UnsafePathError(Exception):
    """Raised when a requested path would escape the sandboxed workspace,
    or otherwise violates a safety rule (blocked extension, too large)."""
    pass


# Extensions CRUZ will never write inside the workspace — a cheap extra
# guardrail against generating something that later gets double-clicked
# or executed.
BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".msi", ".scr", ".vbs"}

# Generous for text/code, but blocks an accidental multi-GB write.
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB


def safe_path(relative_path: str) -> Path:
    """
    Resolve a path the LLM supplied against WORKSPACE_ROOT and guarantee
    the result cannot escape it — blocks '..' traversal, absolute paths,
    drive-letter switches, symlink tricks, etc.

    Every function in tools/files.py calls this before touching disk.
    """
    if relative_path is None or str(relative_path).strip() == "":
        raise UnsafePathError("Path is empty.")

    candidate = (WORKSPACE_ROOT / relative_path).resolve()
    root = WORKSPACE_ROOT.resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        raise UnsafePathError(
            f"'{relative_path}' resolves outside the CRUZ workspace and is not allowed."
        )

    return candidate


def ensure_extension_allowed(path: Path) -> None:
    if path.suffix.lower() in BLOCKED_EXTENSIONS:
        raise UnsafePathError(
            f"CRUZ isn't allowed to create or modify '{path.suffix}' files."
        )


def ensure_within_size_limit(size_bytes: int) -> None:
    if size_bytes > MAX_FILE_BYTES:
        raise UnsafePathError(
            f"File is {size_bytes / 1024 / 1024:.1f} MB, over the "
            f"{MAX_FILE_BYTES / 1024 / 1024:.0f} MB limit."
        )
