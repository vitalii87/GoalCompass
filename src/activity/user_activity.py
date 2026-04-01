# src/activity/user_activity.py

from __future__ import annotations

import ctypes
from ctypes import Structure, byref, c_uint, sizeof


class LASTINPUTINFO(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("dwTime", c_uint),
    ]


class UserActivityMonitor:
    """
    Windows user activity detector.

    Returns:
    - active
    - idle
    """

    def __init__(self, idle_threshold_seconds: int) -> None:
        self.idle_threshold_seconds = idle_threshold_seconds

    def get_idle_seconds(self) -> int:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        last_input_info = LASTINPUTINFO()
        last_input_info.cbSize = sizeof(LASTINPUTINFO)

        success = user32.GetLastInputInfo(byref(last_input_info))
        if not success:
            return 0

        tick_count = kernel32.GetTickCount()
        elapsed_ms = tick_count - last_input_info.dwTime
        if elapsed_ms < 0:
            return 0

        return int(elapsed_ms / 1000)

    def get_activity_state(self) -> str:
        idle_seconds = self.get_idle_seconds()
        if idle_seconds >= self.idle_threshold_seconds:
            return "idle"
        return "active"