from __future__ import annotations

import argparse

from src.services.update_service import UpdateError, check_for_updates, install_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check for or install GoalCompass updates from GitHub."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="install the available update with a fast-forward Git merge",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        status = install_update() if args.install else check_for_updates(fetch=True)
    except UpdateError as error:
        print(f"GoalCompass update failed: {error}")
        return 1

    if status.update_available:
        print(
            f"GoalCompass {status.remote_version} is available; "
            f"local version is {status.local_version}."
        )
        print("Close GoalCompass and run: python update_goalcompass.py --install")
        return 0

    print(f"GoalCompass {status.local_version} is up to date.")
    if args.install:
        print("Restart GoalCompass if program files were updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
