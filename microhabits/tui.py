"""Provied curses TUI. Handles rendering a grid with dates and statuses, managing user input."""

import curses
import datetime
from dataclasses import dataclass
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

type Position = tuple[int, int]
type RowSegment = tuple[str, int]
type Row = list[RowSegment]


class _Pad:
    """Helper for managing text contents in curses pads."""

    def __init__(self) -> None:
        """Initialize the Pad with an empty contents list."""
        self.pad: curses.window
        self.contents: list[Row] = []

    def add_str(self, content: str, attr: int = curses.A_NORMAL) -> None:
        """Adds row to list of contents"""
        self.contents.append([(content, attr)])

    def add_segments(self, segments: Row) -> None:
        """Adds a row composed of multiple styled text segments."""
        self.contents.append(segments)

    def get_height(self) -> int:
        """Returns height of pad, i.e. number of rows."""
        return len(self.contents)

    def get_width(self) -> int:
        """Returns widest row in pad."""
        return max(sum(len(content) for content, _ in row) for row in self.contents)

    def refresh(self, pad_min: Position, screen_min: Position, screen_max: Position):
        """Shows the pad at the specified position"""
        self.pad = curses.newpad(self.get_height() + 1, self.get_width() + 1)
        for row, segments in enumerate(self.contents):
            col = 0
            for content, attr in segments:
                self.pad.addstr(row, col, content, attr)
                col += len(content)
        pminrow, pmincol = pad_min
        sminrow, smincol = screen_min
        smaxrow, smaxcol = screen_max
        self.pad.refresh(pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol)

    def __repr__(self) -> str:
        """Return the string representation of the pad contents."""
        return "\n".join(
            "".join(content for content, _ in row) for row in self.contents
        )


@dataclass
class TuiState:
    """Manages state of TUI."""

    tui_habits: list[Habit]
    today: datetime.date = datetime.date.today()
    curses_loop: bool = True

    def __post_init__(self) -> None:
        self.selected_date = self.today
        self.selected_habit = self.tui_habits[0]


def _format_name(
    habit: Habit, show_alias: bool, name_cutoff: int, cutoff_char: str
) -> str:
    name = habit.get_alias_or_name() if show_alias else habit.get_name()

    # Add indicator if the habit has an associated file
    if habit.get_file():
        name = f"[f] {name}"

    # Shorten long names
    last_visible_character = name_cutoff - 2
    if len(name) > last_visible_character:
        name = name[:last_visible_character] + cutoff_char

    return name.ljust(name_cutoff)


def _dates_row(
    dates: list[datetime.date],
    today: datetime.date,
    name_cutoff: int,
    pretty_format: str,
    padding: int,
) -> Row:
    segments: Row = [(" " * name_cutoff, curses.A_NORMAL)]
    for date in dates:
        attr = curses.A_BOLD if date == today else curses.A_NORMAL
        segments.append((date.strftime(pretty_format).ljust(padding), attr))
    return segments


def _decide_toggle(habit: Habit, date: datetime.date, padding: int) -> str:
    if s := habit.get_status(date):
        toggle_char = STATUSES_DISPLAY[s]
    elif habit.is_due(date):
        toggle_char = " "
    else:
        toggle_char = "o"
    return f"[{toggle_char}]".ljust(padding)


def _decide_attr(is_selected: bool, hide_completed: bool, is_due: bool) -> int:
    if hide_completed and not is_due:
        attr = curses.A_DIM
    else:
        attr = curses.A_BOLD
    if is_selected:
        attr |= curses.A_STANDOUT
    return attr


def _get_selected_index(habits: list[Habit], habit: Habit):
    return habits.index(habit)


def _refresh_pads(
    stdscr,
    header_pad: _Pad,
    habits_pad: _Pad,
    selected_habits_nr: int,
    scroll_margin: int,
):
    y_max, x_max = (p - 1 for p in stdscr.getmaxyx())
    header_bottom = header_pad.get_height() - 1
    scroll = max(0, selected_habits_nr - y_max + header_bottom + scroll_margin)
    header_pad.refresh((0, 0), (0, 0), (header_bottom, x_max))
    habits_pad.refresh((scroll, 0), (header_bottom + 1, 0), (y_max, x_max))


def _handle_keypress(key: str, tui: TuiState, options: OptionsManager, stdscr) -> None:
    if key in KEYBINDS:
        KEYBINDS[key](tui=tui, options=options, stdscr=stdscr)


def run(stdscr, habits_manager: HabitsManager, options: OptionsManager):
    """Start TUI."""
    tui = TuiState(habits_manager.get_unhidden())

    # if time is between 00:00 and 03:00, stay on previous day
    if datetime.time(0, 0) <= datetime.datetime.now().time() < datetime.time(3, 0):
        tui.selected_date -= timedelta(days=1)

    curses.curs_set(0)  # hide cursor
    stdscr.refresh()  # needed so everything displays at program start without a keypress

    while tui.curses_loop:
        header_pad = _Pad()
        habits_pad = _Pad()
        date_padding = options.get("date_padding")
        name_cutoff = options.get("name_cutoff")

        # The marker for the selected date
        header_pad.add_str(
            " " * (name_cutoff + date_padding * options.get("days_back"))
            + "-" * date_padding,
            attr=curses.A_BOLD,
        )

        on_screen_dates = [
            tui.selected_date + timedelta(days=delta)
            for delta in range(
                -options.get("days_back"), options.get("days_forward") + 1
            )
        ]

        # Row of dates to be shown
        header_pad.add_segments(
            _dates_row(
                on_screen_dates,
                tui.today,
                name_cutoff,
                options.get("pretty_date_format"),
                date_padding,
            )
        )

        # Add habits to pad
        for habit in tui.tui_habits:
            habit_row: str = _format_name(
                habit,
                options.get("show_alias"),
                options.get("name_cutoff"),
                options.get("name_cutoff_char"),
            )

            # Add toggle for each date shown
            for date in on_screen_dates:
                habit_row += _decide_toggle(habit, date, date_padding)

            habits_pad.add_str(
                habit_row,
                attr=_decide_attr(
                    is_selected=habit == tui.selected_habit,
                    hide_completed=options.get("hide_completed"),
                    is_due=habit.is_due(tui.selected_date),
                ),
            )

        # Refresh all pads at once.
        curses.update_lines_cols()  # detect screen resize

        _refresh_pads(
            stdscr,
            header_pad,
            habits_pad,
            selected_habits_nr=_get_selected_index(tui.tui_habits, tui.selected_habit),
            scroll_margin=options.get("scroll_margin"),
        )

        _handle_keypress(stdscr.getkey(), tui, options, stdscr)
