from __future__ import annotations

import argparse


COMPONENTS = ("runner", "tracker", "overlay", "control-panel", "setup")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--component", choices=COMPONENTS, default="runner")
    return parser


def main() -> None:
    component = build_parser().parse_known_args()[0].component

    if component == "tracker":
        from src.main import main as component_main
    elif component == "overlay":
        from gui.overlay_widget import main as component_main
    elif component == "control-panel":
        from gui.control_panel import main as component_main
    elif component == "setup":
        from gui.setup_wizard import main as component_main
    else:
        from run_goalcompass import main as component_main

    component_main()


if __name__ == "__main__":
    main()
