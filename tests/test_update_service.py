from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from src.services.update_service import (
    UpdateError,
    UpdateStatus,
    download_release_installer,
    fetch_latest_release,
    install_update,
    is_newer_version,
    parse_semver,
    release_status_from_payload,
)


class SemanticVersionTests(unittest.TestCase):
    def test_parse_semver(self) -> None:
        self.assertEqual(parse_semver("2.4.1"), (2, 4, 1, ""))
        self.assertEqual(parse_semver("1.0.0-beta.2"), (1, 0, 0, "beta.2"))

    def test_invalid_semver_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid semantic version"):
            parse_semver("version-2")

    def test_newer_version_handles_stable_and_prerelease(self) -> None:
        self.assertTrue(is_newer_version("0.4.0", "0.3.1"))
        self.assertTrue(is_newer_version("1.0.0", "1.0.0-beta.1"))
        self.assertFalse(is_newer_version("1.0.0-beta.1", "1.0.0"))


class GitHubReleaseUpdateTests(unittest.TestCase):
    def release_payload(self, data: bytes = b"installer") -> dict:
        digest = hashlib.sha256(data).hexdigest()
        return {
            "tag_name": "v0.4.0",
            "html_url": "https://github.com/vitalii87/GoalCompass/releases/tag/v0.4.0",
            "assets": [
                {
                    "name": "GoalCompass-Setup-0.4.0.exe",
                    "browser_download_url": "https://example.test/GoalCompass-Setup-0.4.0.exe",
                    "digest": f"sha256:{digest}",
                }
            ],
        }

    def test_release_payload_selects_versioned_installer(self) -> None:
        status = release_status_from_payload(self.release_payload(), "0.3.1")

        self.assertTrue(status.update_available)
        self.assertEqual(status.remote_version, "0.4.0")
        self.assertEqual(status.asset_name, "GoalCompass-Setup-0.4.0.exe")

    def test_private_repository_uses_authenticated_gh_fallback(self) -> None:
        private_error = HTTPError(
            "https://api.github.test/latest",
            404,
            "Not Found",
            hdrs=None,
            fp=None,
        )
        payload = self.release_payload()
        with (
            patch("src.services.update_service.urlopen", side_effect=private_error),
            patch(
                "src.services.update_service.fetch_latest_release_with_gh",
                return_value=payload,
            ) as fallback_mock,
        ):
            result = fetch_latest_release()

        self.assertEqual(result, payload)
        fallback_mock.assert_called_once_with()

    def test_downloaded_installer_digest_is_verified(self) -> None:
        data = b"verified installer"
        status = release_status_from_payload(self.release_payload(data), "0.3.1")

        class FakeResponse:
            def __init__(self) -> None:
                self.remaining = data

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

            def read(self, _size: int = -1) -> bytes:
                result, self.remaining = self.remaining, b""
                return result

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch(
                    "src.services.update_service.UPDATE_DOWNLOAD_DIR",
                    Path(temp_dir),
                ),
                patch(
                    "src.services.update_service.urlopen",
                    return_value=FakeResponse(),
                ),
            ):
                installer_path = download_release_installer(status)

            self.assertEqual(installer_path.read_bytes(), data)

    def test_installed_update_downloads_and_starts_setup(self) -> None:
        status = release_status_from_payload(self.release_payload(), "0.3.1")
        installer_path = Path("GoalCompass-Setup-0.4.0.exe")

        with (
            patch("src.services.update_service.IS_FROZEN", True),
            patch(
                "src.services.update_service.check_release_updates",
                return_value=status,
            ),
            patch(
                "src.services.update_service.download_release_installer",
                return_value=installer_path,
            ),
            patch("src.services.update_service.launch_installer") as launch_mock,
        ):
            result = install_update()

        self.assertTrue(result.installer_started)
        self.assertEqual(result.installer_path, str(installer_path))
        launch_mock.assert_called_once_with(installer_path)


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
