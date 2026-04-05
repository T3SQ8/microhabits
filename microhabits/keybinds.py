"""Contains functions ran via keyinds from TUI"""

# pylint: disable=missing-function-docstring

from __future__ import annotations

import inspect
import os
import subprocess
from datetime import timedelta
from functools import wraps
from typing import TYPE_CHECKING

from microhabits.options import OptionsManager

if TYPE_CHECKING:
    from .tui import TuiState

EDITOR = os.getenv("EDITOR", "vi")


def keybind_handler(func):
    sig = inspect.signature(func)
    allowed = set(sig.parameters)

    @wraps(func)
    def wrapper(*args, **kwargs):
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        return func(*args, **filtered_kwargs)

    return wrapper


def _move_vertical(tui: TuiState, distance: int):
    current_selected = tui.tui_habits.index(tui.selected_habit)
    new_selected = (current_selected + distance) % len(tui.tui_habits)
    tui.selected_habit = tui.tui_habits[new_selected]


def _move_horizontal(tui: TuiState, distance: int):
    tui.selected_date += timedelta(days=distance)


@keybind_handler
def move_up(*_, tui: TuiState):
    _move_vertical(tui, -1)


@keybind_handler
def move_down(*_, tui: TuiState):
    _move_vertical(tui, 1)


@keybind_handler
def move_left(*_, tui: TuiState):
    _move_horizontal(tui, -1)


@keybind_handler
def move_right(*_, tui: TuiState):
    _move_horizontal(tui, 1)


@keybind_handler
def move_top(*_, tui: TuiState):
    tui.selected_habit = tui.tui_habits[0]


@keybind_handler
def move_bottom(*_, tui: TuiState):
    tui.selected_habit = tui.tui_habits[-1]


@keybind_handler
def move_today(*_, tui: TuiState):
    tui.selected_date = tui.today


@keybind_handler
def halt(*_, tui: TuiState):
    tui.curses_loop = False


@keybind_handler
def next_status(*_, tui: TuiState):
    tui.selected_habit.next_status(tui.selected_date)


@keybind_handler
def next_status_all(*_, tui: TuiState):
    tui.selected_habit.next_status(tui.selected_date)
    wanted_status = tui.selected_habit.get_status(tui.selected_date)
    for habit in tui.tui_habits:
        habit.set_status(tui.selected_date, wanted_status)


@keybind_handler
def toggle_hide_completed(*_, options: OptionsManager):
    options.toggle_option("hide_completed")


@keybind_handler
def toggle_show_aliases(*_, options: OptionsManager):
    options.toggle_option("show_alias")


@keybind_handler
def open_in_editor(*_, tui: TuiState, stdscr):
    if file := tui.selected_habit.get_file():
        subprocess.run([EDITOR, os.path.expanduser(file)], check=False)
    stdscr.clear()
    stdscr.refresh()
