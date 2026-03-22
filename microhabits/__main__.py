"""
Command-line interface for microhabit. Parses command-line arguments, determines default
configurations based on XDG Base Directory specification and launches TUI.
"""

import argparse
import sys
from curses import wrapper
from os import getenv
from pathlib import Path

from filelock import FileLock, Timeout

from .habits_collection import HabitsManager
from .tui import CursesTui

LOCK_FILE = "/tmp/microhabits.lock"

XDG_CONFIG_HOME = Path(getenv("XDG_CONFIG_HOME", default=Path.home() / ".config"))
XDG_DATA_HOME = Path(getenv("XDG_DATA_HOME", default=Path.home() / ".local/share"))

DEFAULT_HABITS_FILE = XDG_CONFIG_HOME / "microhabits/habits.yml"
DEFAULT_LOG_FILE = XDG_DATA_HOME / "microhabits/log.csv"
DEFAULT_CONF_FILE = XDG_CONFIG_HOME / "microhabits/options.yml"


def main():
    """
    Entry point for command-line interface. Parses command-line arguments, determines default
    configurations based on XDG Base Directory specification and launches TUI. Ensures that only one
    instance runs at a time by acquiring a file lock and exits with a non-zero status if another
    instance is already active.
    """
    parser = argparse.ArgumentParser(
        description="minimalistic habit tracker",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,  # prints defaults in help message
    )

    parser.add_argument(
        "-f",
        "--file",
        metavar="FILE",
        dest="habits_file",
        type=Path,
        default=DEFAULT_HABITS_FILE,
        help="specify the habits file in YAML format",
    )
    parser.add_argument(
        "-c",
        "--conf",
        metavar="FILE",
        dest="conf_file",
        type=Path,
        default=DEFAULT_CONF_FILE,
        help="specify CSV file for logging activity",
    )
    parser.add_argument(
        "-l",
        "--log",
        metavar="FILE",
        dest="log_file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help="specify CSV file for logging activity",
    )

    args = parser.parse_args()

    try:
        with FileLock(LOCK_FILE, timeout=0):
            start_tui(args.habits_file, args.log_file, args.conf_file)
    except Timeout:
        print("Another instance is already running. Exiting.")
        sys.exit(1)


def start_tui(habits_file, log_file, conf_file):
    habits = HabitsManager(habits_file, log_file)

    tui = CursesTui(habits, conf_file if conf_file.is_file() else None)
    wrapper(tui.run)
    habits.save_log_to_file()


if __name__ == "__main__":
    main()
