# run_goalcompass.py

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


ROOT_DIR = Path(__file__).resolve().parent

TRACKER_SCRIPT = ROOT_DIR / "src" / "main.py"
OVERLAY_SCRIPT = ROOT_DIR / "gui" / "overlay_widget.py"
CONTROL_PANEL_SCRIPT = ROOT_DIR / "gui" / "control_panel.py"


def log(message: str) -> None:
    print(f"[GoalCompass Runner] {message}", flush=True)


def start_process(script_path: Path, name: str) -> subprocess.Popen:
    if not script_path.exists():
        raise FileNotFoundError(f"{name} script not found: {script_path}")

    log(f"Starting {name}: {script_path}")

    return subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(ROOT_DIR),
    )


def stop_process(process: Optional[subprocess.Popen], name: str) -> None:
    if process is None:
        return

    if process.poll() is not None:
        log(f"{name} already stopped.")
        return

    log(f"Stopping {name}...")

    process.terminate()

    try:
        process.wait(timeout=5)
        log(f"{name} stopped.")
    except subprocess.TimeoutExpired:
        log(f"{name} did not stop gracefully. Killing...")
        process.kill()
        process.wait(timeout=5)
        log(f"{name} killed.")


def main() -> None:
    tracker_process: Optional[subprocess.Popen] = None
    overlay_process: Optional[subprocess.Popen] = None

    try:
        tracker_process = start_process(TRACKER_SCRIPT, "tracker")

        # Small delay so tracker can create/update current_state.json first.
        time.sleep(1)

        overlay_process = start_process(OVERLAY_SCRIPT, "overlay")

        log("GoalCompass is running.")
        log("Press Ctrl+C here to stop tracker + overlay.")
        log("Control Panel can still be opened separately:")
        log(f"  {sys.executable} {CONTROL_PANEL_SCRIPT}")

        while True:
            time.sleep(2)

            tracker_code = tracker_process.poll() if tracker_process else None
            overlay_code = overlay_process.poll() if overlay_process else None

            if tracker_code is not None:
                log(f"Tracker exited with code {tracker_code}.")
                break

            if overlay_code is not None:
                log(f"Overlay exited with code {overlay_code}.")
                log("Tracker is still running. Stopping runner now.")
                break

    except KeyboardInterrupt:
        log("Stop requested by user.")

    except Exception as error:
        log(f"Runner error: {error}")

    finally:
        stop_process(overlay_process, "overlay")
        stop_process(tracker_process, "tracker")
        log("GoalCompass stopped.")


if __name__ == "__main__":
    main()