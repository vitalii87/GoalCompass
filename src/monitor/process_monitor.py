# src/monitor/process_monitor.py

from __future__ import annotations

from typing import Dict

import psutil
import win32gui
import win32process


def get_foreground_process_info() -> Dict[str, str]:
    """
    Returns normalized foreground process info:
    {
        "process_name": "chrome.exe",
        "window_title": "YouTube - Google Chrome"
    }
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {
                "process_name": "unknown.exe",
                "window_title": "",
            }

        window_title = win32gui.GetWindowText(hwnd) or ""

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return {
                "process_name": "unknown.exe",
                "window_title": window_title,
            }

        process = psutil.Process(pid)
        process_name = process.name().lower()

        return {
            "process_name": process_name,
            "window_title": window_title,
        }

    except Exception:
        return {
            "process_name": "unknown.exe",
            "window_title": "",
        }