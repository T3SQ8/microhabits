import argparse
from os import getenv
from os.path import expanduser
from pathlib import Path

from .tui import main as tui_main


def main():
    xdg_config_home = Path(getenv("XDG_CONFIG_HOME", expanduser("~/.config")))
    xdg_data_home = Path(getenv("XDG_DATA_HOME", expanduser("~/.local/share")))
    default_habits_file = xdg_config_home / "microhabits/habits.yml"
    default_log_file = xdg_data_home / "microhabits/log.csv"

    parser = argparse.ArgumentParser(description="minimalistic habit tracker")

    parser.add_argument(
        "-f",
        "--file",
        metavar="FILE",
        dest="habits_file",
        default=default_habits_file,
        help="specify the habits file in YAML format (default: %(default)s)",
    )
    parser.add_argument(
        "-l",
        "--log",
        metavar="FILE",
        dest="log_file",
        default=default_log_file,
        help="specify CSV file for logging activity (default: %(default)s)",
    )

    args = parser.parse_args()
    tui_main(args.habits_file, args.log_file)


if __name__ == "__main__":
    main()
