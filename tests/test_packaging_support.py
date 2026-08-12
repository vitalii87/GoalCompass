from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from run_goalcompass import component_command
from src.version import read_version


class PackagedRunnerTests(unittest.TestCase):
    def test_source_component_uses_python_script(self) -> None:
        script = Path("gui/control_panel.py")
        with patch("run_goalcompass.IS_FROZEN", False):
            command = component_command("control-panel", script)
        self.assertEqual(command, [sys.executable, str(script)])

    def test_frozen_component_reuses_application_executable(self) -> None:
        with patch("run_goalcompass.IS_FROZEN", True):
            command = component_command("tracker", Path("unused.py"))
        self.assertEqual(command, [sys.executable, "--component", "tracker"])

    def test_packaged_version_file_can_be_read(self) -> None:
        self.assertEqual(read_version(Path("VERSION")), "0.3.1")


if __name__ == "__main__":
    unittest.main()
