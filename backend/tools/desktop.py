"""
Desktop automation tools: App launcher, process manager, and window control.
"""
import sys
import subprocess
import psutil
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger("tools.desktop")

# Extended Windows Process Mapping
APP_MAPPINGS = {
    "notepad": ["notepad.exe"],
    "calc": ["calc.exe", "calculatorapp.exe", "calculator.exe"],
    "calculator": ["calc.exe", "calculatorapp.exe", "calculator.exe"],
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "code": ["code.exe"],
    "vscode": ["code.exe"],
    "vs code": ["code.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "explorer": ["explorer.exe"],
    "taskmgr": ["taskmgr.exe"],
    "spotify": ["spotify.exe"],
    "vlc": ["vlc.exe"],
    "paint": ["mspaint.exe"],
    "gemini": ["gemini.exe"],
}


def _close_windows_by_title(title_substring: str) -> int:
    """
    Finds and posts WM_CLOSE to all top-level Windows GUI windows
    whose title contains title_substring (case-insensitive).
    """
    if sys.platform != "win32":
        return 0

    closed = 0
    sub_lower = title_substring.lower()

    try:
        import win32gui
        import win32con

        def enum_win_cb(hwnd, extra):
            nonlocal closed
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd) or ""
                    if title and sub_lower in title.lower():
                        logger.info(f"Posting WM_CLOSE to window: '{title}' (hwnd={hwnd})")
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        closed += 1
            except Exception:
                pass
            return True

        win32gui.EnumWindows(enum_win_cb, None)
    except Exception as e:
        logger.debug(f"Window title search error: {e}")

    return closed


async def launch_app(app_name: str, args: Optional[str] = None) -> Dict[str, Any]:
    """
    Launches a desktop application by name or path (e.g. Notepad, Calculator, VS Code, Chrome, Spotify, Paint, VLC, Gemini).
    """
    clean_name = app_name.lower().strip()

    if clean_name == "gemini":
        target_cmd = "https://gemini.google.com"
    else:
        target_list = APP_MAPPINGS.get(clean_name, [app_name])
        target_cmd = target_list[0]

    try:
        if sys.platform == "win32":
            if args:
                cmd = f'start "" "{target_cmd}" {args}'
            else:
                cmd = f'start "" "{target_cmd}"'
            subprocess.Popen(cmd, shell=True)
        else:
            full_command = f"{target_cmd} {args}" if args else target_cmd
            subprocess.Popen(full_command.split())
        logger.info(f"Successfully launched desktop app/link: {clean_name}")
        return {"success": True, "app": app_name, "message": f"Successfully launched {app_name}"}
    except Exception as e:
        logger.error(f"Failed to launch app {app_name}: {e}")
        return {"success": False, "app": app_name, "error": str(e)}


async def close_app(app_name: str) -> Dict[str, Any]:
    """
    Closes a running desktop application, PWA, or browser window/tab by name or title (e.g. notepad, calculator, chrome, gemini).
    Uses win32gui window title matching (WM_CLOSE), browser tab matching, psutil process tree, and taskkill.
    """
    clean_name = app_name.lower().strip()
    target_exes = APP_MAPPINGS.get(clean_name, [clean_name, f"{clean_name}.exe"])

    closed_count = 0

    try:
        # 1. Close any open Windows GUI window matching title (e.g., "Gemini - Google Chrome", "Gemini")
        win_closed = _close_windows_by_title(clean_name)
        closed_count += win_closed

        # 2. Check if CRUZ browser manager has a matching active tab open (e.g. gemini.google.com)
        try:
            from services.browser_manager import browser_manager
            state = await browser_manager.get_state()
            if state.get("open"):
                url = (state.get("url") or "").lower()
                title = (state.get("title") or "").lower()
                if clean_name in url or clean_name in title:
                    res = await browser_manager.close_tab()
                    if res.get("success"):
                        closed_count += 1
                        logger.info(f"Closed internal browser tab matching '{clean_name}' ({url})")
        except Exception as e:
            logger.debug(f"Browser tab check skipped: {e}")

        # 3. Fast kill matching processes via psutil (name-only)
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = (proc.info['name'] or '').lower()
                matches = False

                for target in target_exes:
                    t_clean = target.lower()
                    if t_clean == pname or t_clean in pname:
                        matches = True
                        break

                if not matches and len(clean_name) >= 3 and clean_name in pname:
                    matches = True

                if matches:
                    proc.kill()
                    closed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # 4. Fallback taskkill on Windows for exact exes (skipping broad browsers unless explicitly asked)
        if sys.platform == "win32" and clean_name not in ["chrome", "google chrome", "edge"]:
            for exe in target_exes:
                exe_name = exe if exe.endswith(".exe") else f"{exe}.exe"
                res = subprocess.run(
                    f"taskkill /IM {exe_name} /F /T",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0:
                    closed_count += 1

        if closed_count > 0:
            logger.info(f"Successfully closed '{app_name}' (closed {closed_count} instances/windows/tabs)")
            return {
                "success": True,
                "app": app_name,
                "message": f"Successfully closed {app_name}",
                "instances_closed": closed_count,
            }
        else:
            return {
                "success": False,
                "app": app_name,
                "error": f"No active process, window, or browser tab found for '{app_name}'. Make sure {app_name} is open.",
            }
    except Exception as e:
        logger.error(f"Error closing app {app_name}: {e}")
        return {"success": False, "app": app_name, "error": str(e)}
