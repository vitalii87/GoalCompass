from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.version import VERSION_PATH, read_version


ROOT_DIR = Path(__file__).resolve().parents[2]
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
