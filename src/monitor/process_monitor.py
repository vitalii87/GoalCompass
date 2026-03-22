import psutil
import win32gui
import win32process


def get_active_process_info() -> dict:
    """
    Повертає інформацію про активне вікно:
    - pid
    - process_name
    - window_title

    Якщо щось пішло не так — повертає safe fallback.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return {
                "pid": None,
                "process_name": "unknown",
                "window_title": "",
            }

        window_title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        process = psutil.Process(pid)
        process_name = process.name()

        return {
            "pid": pid,
            "process_name": process_name,
            "window_title": window_title,
        }

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return {
            "pid": None,
            "process_name": "unknown",
            "window_title": "",
        }
    except Exception as e:
        return {
            "pid": None,
            "process_name": "unknown",
            "window_title": f"error: {e}",
        }


def get_active_process() -> str:
    """
    Залишаємо для сумісності з поточним main.py
    """
    return get_active_process_info()["process_name"]