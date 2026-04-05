"""Provied curses TUI. Handles rendering a grid with dates and statuses, managing user input."""

import curses
import datetime
from datetime import timedelta
from typing import Callable

from . import keybinds
from .habit import Habit
from .habits_collection import HabitsManager
from .options import OptionsManager

STATUSES_DISPLAY = {
    None: " ",
    "COMPLETED": "y",
    "SKIPPED": "s",
    "FAILED": "n",
}

KEYBINDS: dict[str, Callable] = {
    "KEY_UP": keybinds.move_up,
    "k": keybinds.move_up,
    "KEY_DOWN": keybinds.move_down,
    "j": keybinds.move_down,
    "KEY_LEFT": keybinds.move_left,
    "h": keybinds.move_left,
    "KEY_RIGHT": keybinds.move_right,
    "l": keybinds.move_right,
    " ": keybinds.next_status,
    "t": keybinds.move_today,
    "q": keybinds.halt,
    "H": keybinds.toggle_hide_completed,
    "A": keybinds.toggle_show_aliases,
    "g": keybinds.move_top,
    "G": keybinds.move_bottom,
    "E": keybinds.open_in_editor,
    "S": keybinds.next_status_all,
}


class _Pad:
    """Helper for managing text contents in curses pads."""

    def __init__(self) -> None:
        """Initialize the Pad with an empty contents list."""
        self.pad: curses.window
        self.contents: list[tuple[str, int]] = []

    def add_str(
        self, content: str, attr: int = curses.A_NORMAL, padding: int = 0
    ) -> None:
        """Adds row to list of contents"""
        self.contents.append((content.rjust(padding), attr))

    def get_height(self) -> int:
        """Returns height of pad, i.e. number of rows."""
        return len(self.contents)

    def get_width(self) -> int:
        """Returns widest row in pad."""
        return max(len(content) for content, _ in self.contents)

    def refresh(self, pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol):
        """Shows the pad at the specified position"""
        self.pad = curses.newpad(self.get_height() + 1, self.get_width() + 1)
        for row, content in enumerate(self.contents):
            self.pad.addstr(row, 0, content[0], content[1])
        self.pad.refresh(pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol)

    def __repr__(self) -> str:
        """Return the string representation of the pad contents."""
        return "\n".join(c[0] for c in self.contents)


class CursesTui:
    """TUI-interface for the program."""

    def __init__(self, habits: HabitsManager, options: OptionsManager) -> None:
        self.curses_loop = True
        self.habits_manager: HabitsManager = habits
        self.options: OptionsManager = options
        self.today: datetime.date = datetime.date.today()
        self.stdscr: curses.window = curses.initscr()

        # ignore habits that only exist in log file, see load_log_from_file()
        self.tui_habits = self.habits_manager.get_unhidden()
        self.selected_habit = self.tui_habits[0]

        # if time is between 00:00 and 03:00, stay on previous day
        self.selected_date = (
            self.today - timedelta(days=1)
            if (
                datetime.time(0, 0)
                <= datetime.datetime.now().time()
                < datetime.time(3, 0)
            )
            else self.today
        )

    def run(self, stdscr) -> None:
        """Start the main TUI event loop."""
        self.stdscr = stdscr

        def _format_name(habit: Habit) -> str:
            name = (
                habit.get_alias_or_name()
                if self.options.get("show_alias")
                else habit.get_name()
            )

            # Add indicator if the habit has an associated file
            if habit.get_file():
                name = f"[f] {name}"

            # Shorten long names
            last_visible_character = name_cutoff - 2
            if len(name) > last_visible_character:
                name = name[:last_visible_character] + self.options.get(
                    "name_cutoff_char"
                )

            return name.ljust(name_cutoff)

        curses.curs_set(0)  # hide cursor
        stdscr.refresh()  # needed so everything displays at program start without a keypress

        while self.curses_loop:
            header_pad = _Pad()
            habits_pad = _Pad()
            date_padding = self.options.get("date_padding")
            name_cutoff = self.options.get("name_cutoff")

            header_pad.add_str("MICROHABITS".rjust(name_cutoff), attr=curses.A_BOLD)

            # The marker for the selected date
            header_pad.add_str(
                " " * (name_cutoff + date_padding * self.options.get("days_back"))
                + "-" * date_padding,
                attr=curses.A_BOLD,
            )

            # Choose dates to be shown
            on_screen_dates = [
                self.selected_date + timedelta(days=delta)
                for delta in range(
                    -self.options.get("days_back"), self.options.get("days_forward") + 1
                )
            ]

            shown_dates = " " * name_cutoff
            for date in on_screen_dates:
                shown_dates += date.strftime(
                    self.options.get("pretty_date_format")
                ).ljust(date_padding)

            header_pad.add_str(shown_dates)

            # Add habits to pad
            for habit in self.tui_habits:
                habit_row: str = _format_name(habit)

                # Add toggle for each date shown
                for date in on_screen_dates:
                    if s := habit.log.get_status(date):
                        toggle = f"[{STATUSES_DISPLAY[s]}]"
                    elif habit.is_due(date):
                        toggle = "[ ]"
                    else:
                        toggle = "[o]"
                    habit_row += toggle.ljust(date_padding)

                # Highlight rows depending on options and selected toggle
                if self.options.get("hide_completed") and not habit.is_due(
                    self.selected_date
                ):
                    attr = curses.A_DIM
                else:
                    attr = curses.A_BOLD

                if habit == self.selected_habit:
                    attr |= curses.A_STANDOUT

                habits_pad.add_str(habit_row, attr=attr)

            # Refresh all pads at once.
            curses.update_lines_cols()  # detect screen resize
            y_max, x_max = (p - 1 for p in stdscr.getmaxyx())

            i = self.tui_habits.index(self.selected_habit)
            header_bottom = header_pad.get_height() - 1
            scroll = max(
                0, i - y_max + header_bottom + self.options.get("scroll_margin")
            )
            header_pad.refresh(0, 0, 0, 0, header_bottom, x_max)
            habits_pad.refresh(scroll, 0, header_bottom + 1, 0, y_max, x_max)

            key = stdscr.getkey()
            if key in KEYBINDS:
                KEYBINDS[key](self)
            else:
                print(key)
