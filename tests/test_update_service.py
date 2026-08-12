from __future__ import annotations

import unittest
from unittest.mock import patch

from src.services.update_service import (
    UpdateError,
    UpdateStatus,
    install_update,
    parse_semver,
)


class SemanticVersionTests(unittest.TestCase):
    def test_parse_semver(self) -> None:
        self.assertEqual(parse_semver("2.4.1"), (2, 4, 1, ""))
        self.assertEqual(parse_semver("1.0.0-beta.2"), (1, 0, 0, "beta.2"))

    def test_invalid_semver_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid semantic version"):
            parse_semver("version-2")


class InstallUpdateTests(unittest.TestCase):
    def test_install_is_blocked_by_tracked_local_changes(self) -> None:
        with patch(
            "src.services.update_service.tracked_local_changes",
            return_value=[" M src/main.py"],
        ):
            with self.assertRaisesRegex(UpdateError, "uncommitted changes"):
                install_update()

    def test_install_fast_forwards_to_upstream(self) -> None:
        before = UpdateStatus("0.1.0", "0.2.0", 2, 0, True, "origin/master")
        after = UpdateStatus("0.2.0", "0.2.0", 0, 0, False, "origin/master")

        with (
            patch(
                "src.services.update_service.tracked_local_changes",
                return_value=[],
            ),
            patch(
                "src.services.update_service.check_for_updates",
                side_effect=[before, after],
            ) as check_mock,
            patch("src.services.update_service.run_git") as git_mock,
        ):
            result = install_update()

        self.assertEqual(result, after)
        git_mock.assert_called_once_with(
            "merge", "--ff-only", "origin/master", timeout=120
        )
        self.assertEqual(check_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
