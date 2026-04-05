"""Contains functions ran via keyinds from TUI"""

# pylint: disable=missing-function-docstring

from __future__ import annotations

import os
import subprocess
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tui import CursesTui

EDITOR = os.getenv("EDITOR", "vi")


def _move_vertical(tui: CursesTui, distance: int):
    current_selected = tui.tui_habits.index(tui.selected_habit)
    new_selected = (current_selected + distance) % len(tui.tui_habits)
    tui.selected_habit = tui.tui_habits[new_selected]


def _move_horizontal(tui: CursesTui, distance: int):
    tui.selected_date += timedelta(days=distance)


def move_up(tui: CursesTui):
    _move_vertical(tui, -1)


def move_down(tui: CursesTui):
    _move_vertical(tui, 1)


def move_left(tui: CursesTui):
    _move_horizontal(tui, -1)


def move_right(tui: CursesTui):
    _move_horizontal(tui, 1)


def move_top(tui: CursesTui):
    tui.selected_habit = tui.tui_habits[0]


def move_bottom(tui: CursesTui):
    tui.selected_habit = tui.tui_habits[-1]


def move_today(tui: CursesTui):
    tui.selected_date = tui.today


def halt(tui: CursesTui):
    tui.curses_loop = False


def next_status(tui: CursesTui):
    tui.selected_habit.next_status(tui.selected_date)


def next_status_all(tui: CursesTui):
    tui.selected_habit.next_status(tui.selected_date)
    wanted_status = tui.selected_habit.get_status(tui.selected_date)
    for habit in tui.tui_habits:
        habit.set_status(tui.selected_date, wanted_status)


def toggle_hide_completed(tui: CursesTui):
    tui.options.toggle_option("hide_completed")


def toggle_show_aliases(tui: CursesTui):
    tui.options.toggle_option("show_alias")


def open_in_editor(tui: CursesTui):
    if file := tui.selected_habit.get_file():
        subprocess.run([EDITOR, os.path.expanduser(file)], check=False)
    tui.stdscr.clear()
    tui.stdscr.refresh()
