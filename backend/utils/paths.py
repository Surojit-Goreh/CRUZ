"""
Central place for filesystem locations CRUZ is allowed to touch.

Every file tool operation is confined to WORKSPACE_ROOT. This is a
deliberate safety boundary: an LLM deciding to call a "delete_path" tool
should never be able to reach outside a sandboxed folder, no matter what
path it's asked (or tricked) into requesting. If you want CRUZ to manage
files elsewhere on the machine later, that's a conscious future decision
(a different, explicitly-scoped tool) — not something that falls out of
a path traversal bug.
"""
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = BACKEND_ROOT / "data"

# Everything tools/files.py does lives under here. This doubles as a
# friendly answer to "where did CRUZ put that file?" — it's always here.
WORKSPACE_ROOT = DATA_ROOT / "workspace"
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

LOGS_ROOT = DATA_ROOT / "logs"
LOGS_ROOT.mkdir(parents=True, exist_ok=True)
