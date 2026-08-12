# run_goalcompass.py

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from src.app_paths import APP_DIR, IS_FROZEN

ROOT_DIR = APP_DIR

TRACKER_SCRIPT = ROOT_DIR / "src" / "main.py"
OVERLAY_SCRIPT = ROOT_DIR / "gui" / "overlay_widget.py"
CONTROL_PANEL_SCRIPT = ROOT_DIR / "gui" / "control_panel.py"
SETUP_WIZARD_SCRIPT = ROOT_DIR / "gui" / "setup_wizard.py"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.services.settings_service import (  # noqa: E402
    is_first_run_completed,
    load_settings,
    should_start_overlay,
    should_start_tracker,
)


def log(message: str) -> None:
    print(f"[GoalCompass Runner] {message}", flush=True)


def component_command(component: str, script_path: Path) -> list[str]:
    if IS_FROZEN:
        return [sys.executable, "--component", component]
    return [sys.executable, str(script_path)]


def start_process(
    script_path: Path,
    name: str,
    component: str,
) -> subprocess.Popen:
    if not IS_FROZEN and not script_path.exists():
        raise FileNotFoundError(f"{name} script not found: {script_path}")

    log(f"Starting {name}: {script_path}")

    return subprocess.Popen(
        component_command(component, script_path),
        cwd=str(ROOT_DIR),
    )


def run_setup_wizard_if_needed() -> bool:
    """
    Returns True if GoalCompass may continue.
    Returns False if setup was cancelled or failed.
    """
    if is_first_run_completed():
        return True

    if not IS_FROZEN and not SETUP_WIZARD_SCRIPT.exists():
        log(f"Setup wizard not found: {SETUP_WIZARD_SCRIPT}")
        return False

    log("First run detected. Starting setup wizard...")

    result = subprocess.run(
        component_command("setup", SETUP_WIZARD_SCRIPT),
        cwd=str(ROOT_DIR),
        check=False,
    )

    if result.returncode != 0:
        log(f"Setup wizard exited with code {result.returncode}.")
        return False

    if not is_first_run_completed():
        log("Setup wizard finished, but first_run_completed is still false.")
        return False

    log("Setup completed.")
    return True


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
        if not run_setup_wizard_if_needed():
            log("GoalCompass startup cancelled.")
            return

        settings = load_settings()

        if should_start_tracker():
            tracker_process = start_process(TRACKER_SCRIPT, "tracker", "tracker")
        else:
            log("Tracker startup disabled in settings.")

        # Small delay so tracker can create/update current_state.json first.
        if tracker_process is not None:
            time.sleep(1)

        if should_start_overlay():
            overlay_process = start_process(OVERLAY_SCRIPT, "overlay", "overlay")
        else:
            log("Overlay startup disabled in settings.")

        if tracker_process is None and overlay_process is None:
            log("Nothing to run. Check settings.")
            return

        log("GoalCompass is running.")
        log("Press Ctrl+C here to stop GoalCompass.")
        log("Control Panel can still be opened separately:")
        log(f"  {sys.executable} {CONTROL_PANEL_SCRIPT}")

        if bool(settings["app"].get("start_control_panel_after_setup", False)):
            start_process(
                CONTROL_PANEL_SCRIPT,
                "control panel",
                "control-panel",
            )

        while True:
            time.sleep(2)

            tracker_code = tracker_process.poll() if tracker_process else None
            overlay_code = overlay_process.poll() if overlay_process else None

            if tracker_process is not None and tracker_code is not None:
                log(f"Tracker exited with code {tracker_code}.")
                break

            if overlay_process is not None and overlay_code is not None:
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
