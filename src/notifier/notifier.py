# src/notifier/notifier.py

from __future__ import annotations


def notify(message: str) -> None:
    print("\n" + "!" * 60)
    print("NOTIFICATION")
    print(message)
    print("!" * 60 + "\n")