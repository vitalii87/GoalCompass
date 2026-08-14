from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.app_paths import APP_DIR, IS_FROZEN, USER_CONFIG_DIR
from src.version import VERSION_PATH, read_version


ROOT_DIR = APP_DIR
GITHUB_REPOSITORY = "vitalii87/GoalCompass"
LATEST_RELEASE_API_URL = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
UPDATE_DOWNLOAD_DIR = USER_CONFIG_DIR / "updates"
HTTP_USER_AGENT = "GoalCompass-Updater"
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateStatus:
    local_version: str
    remote_version: str
    commits_behind: int
    commits_ahead: int
    update_available: bool
    upstream: str
    release_url: str = ""
    asset_url: str = ""
    asset_name: str = ""
    asset_digest: str = ""
    installer_path: str = ""
    installer_started: bool = False


def parse_semver(version: str) -> tuple[int, int, int, str]:
    match = SEMVER_PATTERN.fullmatch(version.strip())
    if match is None:
        raise ValueError(f"Invalid semantic version: {version!r}")

    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        match.group("prerelease") or "",
    )


def is_newer_version(candidate: str, current: str) -> bool:
    candidate_parts = parse_semver(candidate)
    current_parts = parse_semver(current)
    candidate_core = candidate_parts[:3]
    current_core = current_parts[:3]
    if candidate_core != current_core:
        return candidate_core > current_core

    candidate_prerelease = candidate_parts[3]
    current_prerelease = current_parts[3]
    if candidate_prerelease == current_prerelease:
        return False
    if not candidate_prerelease:
        return bool(current_prerelease)
    if not current_prerelease:
        return False
    return candidate_prerelease > current_prerelease


def github_cli_path() -> str:
    discovered = shutil.which("gh")
    if discovered:
        return discovered
    common_path = Path(r"C:\Program Files\GitHub CLI\gh.exe")
    if common_path.is_file():
        return str(common_path)
    raise UpdateError(
        "This is a private GoalCompass repository. Install and sign in to GitHub "
        "CLI, or publish releases from a public repository."
    )


def run_gh(*args: str, timeout: int = 120) -> str:
    try:
        result = subprocess.run(
            [github_cli_path(), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise UpdateError(f"GitHub CLI update request failed: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise UpdateError(
            "The GoalCompass repository is private and GitHub CLI could not access "
            f"the release. Sign in with `gh auth login`.\n{detail}"
        )
    return result.stdout.strip()


def fetch_latest_release_with_gh() -> dict[str, Any]:
    output = run_gh(
        "api",
        f"repos/{GITHUB_REPOSITORY}/releases/latest",
        timeout=30,
    )
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as error:
        raise UpdateError("GitHub CLI returned invalid release JSON.") from error
    if not isinstance(payload, dict):
        raise UpdateError("GitHub CLI returned an invalid release response.")
    return payload


def fetch_latest_release() -> dict[str, Any]:
    request = Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": HTTP_USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in {401, 403, 404}:
            return fetch_latest_release_with_gh()
        raise UpdateError(
            f"GitHub update check failed with HTTP {error.code}."
        ) from error
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise UpdateError(f"Could not check GitHub releases: {error}") from error

    if not isinstance(payload, dict):
        raise UpdateError("GitHub returned an invalid release response.")
    return payload


def release_status_from_payload(
    payload: dict[str, Any],
    local_version: str,
) -> UpdateStatus:
    tag_name = str(payload.get("tag_name", "")).strip()
    remote_version = tag_name[1:] if tag_name.lower().startswith("v") else tag_name
    try:
        parse_semver(local_version)
        parse_semver(remote_version)
    except ValueError as error:
        raise UpdateError(str(error)) from error

    expected_asset_name = f"GoalCompass-Setup-{remote_version}.exe"
    selected_asset: dict[str, Any] = {}
    assets = payload.get("assets", [])
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", "")).strip()
            if name == expected_asset_name:
                selected_asset = asset
                break

    return UpdateStatus(
        local_version=local_version,
        remote_version=remote_version,
        commits_behind=0,
        commits_ahead=0,
        update_available=is_newer_version(remote_version, local_version),
        upstream="github-release",
        release_url=str(payload.get("html_url", "")).strip(),
        asset_url=str(selected_asset.get("browser_download_url", "")).strip(),
        asset_name=str(selected_asset.get("name", "")).strip(),
        asset_digest=str(selected_asset.get("digest", "")).strip().lower(),
    )


def check_release_updates() -> UpdateStatus:
    return release_status_from_payload(
        fetch_latest_release(),
        local_version=read_version(VERSION_PATH),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_release_installer_with_gh(status: UpdateStatus, destination: Path) -> None:
    run_gh(
        "release",
        "download",
        f"v{status.remote_version}",
        "--repo",
        GITHUB_REPOSITORY,
        "--pattern",
        status.asset_name,
        "--dir",
        str(destination.parent),
        "--clobber",
        timeout=180,
    )


def download_release_installer(status: UpdateStatus) -> Path:
    if not status.update_available:
        raise UpdateError("No newer GoalCompass release is available.")
    if not status.asset_url or not status.asset_name:
        raise UpdateError(
            f"Release {status.remote_version} does not contain the Windows installer."
        )
    if not status.asset_digest:
        raise UpdateError(
            f"Release {status.remote_version} installer has no SHA-256 digest."
        )
    if Path(status.asset_name).name != status.asset_name:
        raise UpdateError("GitHub returned an unsafe installer filename.")

    UPDATE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPDATE_DOWNLOAD_DIR / status.asset_name
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(
        status.asset_url,
        headers={"User-Agent": HTTP_USER_AGENT},
    )

    try:
        with urlopen(request, timeout=120) as response, temporary.open("wb") as file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                file.write(chunk)
        temporary.replace(destination)
    except HTTPError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        if error.code in {401, 403, 404}:
            download_release_installer_with_gh(status, destination)
        else:
            raise UpdateError(
                f"Could not download the GoalCompass installer: {error}"
            ) from error
    except (URLError, TimeoutError, OSError) as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise UpdateError(f"Could not download the GoalCompass installer: {error}") from error

    if not destination.exists() or destination.stat().st_size == 0:
        raise UpdateError("The downloaded GoalCompass installer is empty.")

    algorithm, separator, expected_digest = status.asset_digest.partition(":")
    if algorithm != "sha256" or not separator or not expected_digest:
        destination.unlink(missing_ok=True)
        raise UpdateError("GitHub returned an unsupported installer digest.")
    actual_digest = sha256_file(destination)
    if actual_digest.lower() != expected_digest.lower():
        destination.unlink(missing_ok=True)
        raise UpdateError(
            "Installer SHA-256 verification failed. The downloaded file was removed."
        )

    return destination


def launch_installer(installer_path: Path) -> None:
    if not installer_path.is_file():
        raise UpdateError(f"Installer not found: {installer_path}")
    try:
        subprocess.Popen(
            [str(installer_path)],
            cwd=str(installer_path.parent),
            close_fds=True,
        )
    except OSError as error:
        raise UpdateError(f"Could not start the GoalCompass installer: {error}") from error


def run_git(*args: str, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise UpdateError("Git is not installed or not available in PATH.") from error
    except subprocess.TimeoutExpired as error:
        raise UpdateError("GitHub did not respond before the update timed out.") from error

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise UpdateError(detail)

    return result.stdout.strip()


def get_upstream() -> str:
    try:
        return run_git(
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
        )
    except UpdateError:
        branch = run_git("branch", "--show-current")
        if not branch:
            raise UpdateError("GoalCompass is not on a named Git branch.")
        return f"origin/{branch}"


def count_commits(revision_range: str) -> int:
    value = run_git("rev-list", "--count", revision_range)
    try:
        return int(value)
    except ValueError as error:
        raise UpdateError(f"Git returned an invalid commit count: {value!r}") from error


def tracked_local_changes() -> list[str]:
    output = run_git("status", "--porcelain", "--untracked-files=no")
    return [line for line in output.splitlines() if line.strip()]


def check_for_updates(fetch: bool = True) -> UpdateStatus:
    if IS_FROZEN:
        return check_release_updates()
    if not (ROOT_DIR / ".git").exists():
        raise UpdateError("This GoalCompass installation is not a Git checkout.")

    if fetch:
        run_git("fetch", "--quiet", "origin", timeout=120)

    upstream = get_upstream()
    local_version = read_version(VERSION_PATH)

    try:
        remote_version = run_git("show", f"{upstream}:VERSION").strip()
        parse_semver(remote_version)
    except (UpdateError, ValueError):
        remote_version = local_version

    commits_behind = count_commits(f"HEAD..{upstream}")
    commits_ahead = count_commits(f"{upstream}..HEAD")

    return UpdateStatus(
        local_version=local_version,
        remote_version=remote_version,
        commits_behind=commits_behind,
        commits_ahead=commits_ahead,
        update_available=commits_behind > 0,
        upstream=upstream,
    )


def install_update() -> UpdateStatus:
    if IS_FROZEN:
        status = check_release_updates()
        if not status.update_available:
            return status
        installer_path = download_release_installer(status)
        launch_installer(installer_path)
        return replace(
            status,
            installer_path=str(installer_path),
            installer_started=True,
        )

    changes = tracked_local_changes()
    if changes:
        preview = "\n".join(changes[:8])
        raise UpdateError(
            "Local program files have uncommitted changes. "
            "Commit or discard them before updating.\n" + preview
        )

    before = check_for_updates(fetch=True)
    if not before.update_available:
        return before
    if before.commits_ahead:
        raise UpdateError(
            "The local and GitHub histories have diverged. "
            "Resolve them with Git before using automatic updates."
        )

    run_git("merge", "--ff-only", before.upstream, timeout=120)
    return check_for_updates(fetch=False)
