import curses
import datetime
from datetime import timedelta
from pathlib import Path

from .habit import Habit
from .habits_collection import HabitsManager
from .options import OptionsManager
from .task_functions import open_in_editor

STATUSES_DISPLAY = {
    None: " ",
    "COMPLETED": "y",
    "SKIPPED": "s",
    "FAILED": "n",
}

NAME_CUTOFF = 25
LAST_VISIBLE_CHARACTER = NAME_CUTOFF - 2
NAME_CUTOFF_CHAR = "…"
DATE_PADDING = 14
DAYS_BACK = 1
DAYS_FORWARD = 1
HEADER_HEIGHT = 2

PRETTY_DATE_FORMAT = "%d/%m (%a)"


class _Pad:
    def __init__(self, *, height: int, width: int, x: int, y: int) -> None:
        self.pad: curses.window = curses.newpad(height, width)
        self.x, self.y = x, y

    def add_str(
        self, *, x: int, y: int, text: str, attr: int = curses.A_NORMAL
    ) -> None:
        self.pad.addstr(y, x, text, attr)

    def refresh(self, pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol):
        self.pad.refresh(pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol)


class _Row:
    def __init__(self) -> None:
        self.contents: list[str] = []

    def add(self, _str) -> None:
        self.contents.append(_str)

    def add_start(self, _str) -> None:
        self.contents.insert(0, _str)

    def add_padded(self, _str, spaces_to_right) -> None:
        self.add(_str.ljust(spaces_to_right))

    def get(self) -> str:
        return "".join(self.contents)


class CursesTui:
    def __init__(self, habits: HabitsManager, options_file: Path | None) -> None:
        self.habits_manager: HabitsManager = habits
        self.options: OptionsManager = OptionsManager()
        if options_file:
            self.options.load_conf_file(options_file)
        self.selected_habit_nr = 0
        self.curses_loop = True

        # ignore habits that only exist in log file, see load_log_from_file()
        self.tui_habits: list[Habit] = []
        for habit in self.habits_manager.habits.values():
            if not habit.hide_from_tui:
                self.tui_habits.append(habit)

        self.today = datetime.date.today()
        self.selected_habit_nr = 0

        # if time is between 00:00 and 03:00, stay on previous day
        if datetime.time(0, 0) <= datetime.datetime.now().time() < datetime.time(3, 0):
            self.selected_date = self.today - timedelta(days=1)
        else:
            self.selected_date = self.today

        self.keybinds = {
            "KEY_UP": self.move_up,
            "k": self.move_up,
            "KEY_DOWN": self.move_down,
            "j": self.move_down,
            "KEY_LEFT": self.move_left,
            "h": self.move_left,
            "KEY_RIGHT": self.move_right,
            "l": self.move_right,
            " ": self.next_status,
            "t": self.move_to_today,
            "q": self.stop,
            "H": self.toggle_hide_completed,
            "g": self.move_top,
            "G": self.move_bottom,
            "E": self.open_in_editor,
        }

    def move_up(self, *_):
        self.selected_habit_nr = max(0, self.selected_habit_nr - 1)

    def move_down(self, *_):
        self.selected_habit_nr = min(
            self.selected_habit_nr + 1, len(self.tui_habits) - 1
        )

    def move_left(self, *_):
        self.selected_date -= timedelta(days=1)

    def move_right(self, *_):
        self.selected_date += timedelta(days=1)

    def move_top(self, *_):
        self.selected_habit_nr = 0

    def move_bottom(self, *_):
        self.selected_habit_nr = len(self.tui_habits) - 1

    def next_status(self, *_):
        self.tui_habits[self.selected_habit_nr].log.next_status(self.selected_date)

    def move_to_today(self, *_):
        self.selected_date = self.today

    def stop(self, *_):
        self.curses_loop = False

    def toggle_hide_completed(self, *_):
        self.options.toggle_option("hide_completed")

    def open_in_editor(self, stdscr):
        if file := self.tui_habits[self.selected_habit_nr].get_file():
            open_in_editor(file)
        stdscr.clear()
        stdscr.refresh()

    def run(self, stdscr):
        curses.curs_set(0)  # hide cursor
        header_pad = _Pad(height=HEADER_HEIGHT, width=1000, x=0, y=0)
        habits_pad = _Pad(height=len(self.tui_habits), width=1000, x=0, y=0)

        stdscr.refresh()  # needed so everything displays at program start without a keypress

        while self.curses_loop:
            # The marker for the selected date
            header_pad.add_str(
                x=NAME_CUTOFF + DATE_PADDING * DAYS_BACK,
                y=0,
                text="-" * DATE_PADDING,
            )

            # Show selected date and the chosed number of days before/after
            shown_dates = []
            for delta in range(-DAYS_BACK, DAYS_FORWARD + 1):
                shown_dates.append(self.selected_date + timedelta(days=delta))

            for i, date in enumerate(shown_dates):
                formatted_date = date.strftime(PRETTY_DATE_FORMAT)
                header_pad.add_str(
                    x=NAME_CUTOFF + DATE_PADDING * i,
                    y=1,
                    text=formatted_date,
                    attr=curses.A_BOLD if date == self.today else curses.A_NORMAL,
                )

            # Add habits to pad
            for row, habit in enumerate(self.tui_habits):
                row_contents = _Row()

                name = habit.get_name()

                # Add indicator if the habit has an associated file
                if habit.get_file():
                    name = f"[f] {name}"

                # Shorten long names
                if len(name) > LAST_VISIBLE_CHARACTER:
                    name = name[:LAST_VISIBLE_CHARACTER] + NAME_CUTOFF_CHAR
                row_contents.add_padded(name, NAME_CUTOFF)

                # Add toggle for each date shown
                for i, date in enumerate(shown_dates):
                    if s := habit.log.get_status(date):
                        toggle = f"[{STATUSES_DISPLAY[s]}]"
                    elif habit.is_due(date):
                        toggle = "[ ]"
                    else:
                        toggle = "[o]"
                    row_contents.add_padded(toggle, DATE_PADDING)

                # Highlight rows depending on options and selected toggle
                if self.options.get("hide_completed") and not habit.is_due(
                    self.selected_date
                ):
                    attr = curses.A_DIM
                else:
                    attr = curses.A_BOLD

                if row == self.selected_habit_nr:
                    attr = attr | curses.A_STANDOUT

                habits_pad.add_str(x=0, y=row, text=row_contents.get(), attr=attr)

            # Refresh all pads at once.
            curses.update_lines_cols()
            y_max, x_max = [p - 1 for p in stdscr.getmaxyx()]
            header_pad.refresh(0, 0, 0, 0, HEADER_HEIGHT, x_max)
            scroll = max(0, self.selected_habit_nr - y_max + HEADER_HEIGHT)
            habits_pad.refresh(scroll, 0, HEADER_HEIGHT, 0, y_max, x_max)

            if (key := stdscr.getkey()) in self.keybinds:
                self.keybinds[key](stdscr)
            else:
                print(key)
