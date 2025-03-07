import os
from pathlib import Path
import argparse
import tui

def main():
    if (xdg_config_home := os.getenv('XDG_CONFIG_HOME')):
        xdg_config_home = Path(xdg_config_home)
    else:
        xdg_config_home = Path.home() / ".config"

    if (xdg_data_home := os.getenv('XDG_DATA_HOME')):
        xdg_data_home = Path(xdg_data_home)
    else:
        xdg_data_home = Path.home() / ".local/share"

    default_habits_file = xdg_config_home / "microhabits/habits.yml"
    default_log_file = xdg_data_home / "microhabits/log.csv"

    parser = argparse.ArgumentParser(description='minimalistic habit tracker')

    parser.add_argument('-f', '--file', metavar='FILE', dest='habits_file',
                               default=default_habits_file,
                               help='habits file in YAML format (default: %(default)s)')
    parser.add_argument('-l', '--log', metavar='FILE', dest='log_file',
                               default=default_log_file,
                               help='file to log activity to (default: %(default)s)')

    args = parser.parse_args()
    tui.main(args.habits_file, args.log_file)

if __name__ == '__main__':
    main()
