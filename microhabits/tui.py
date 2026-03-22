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
NAME_CUTOFF_CHAR = "…"
DATE_PADDING = 14
DAYS_BACK = 1
DAYS_FORWARD = 1
HEADER_HEIGHT = 2

PRETTY_DATE_FORMAT = "%d/%m (%a)"


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
        header_pad = curses.newpad(HEADER_HEIGHT, 1000)
        habits_pad = curses.newpad(len(self.tui_habits), 1000)

        stdscr.refresh()  # needed so everything displays at program start without a keypress

        while self.curses_loop:
            # The marker for the selected date
            header_pad.addstr(
                0, NAME_CUTOFF + DATE_PADDING * DAYS_BACK, "-" * DATE_PADDING
            )

            # Show selected date and the chosed number of days before/after
            shown_dates = []
            for delta in range(-DAYS_BACK, DAYS_FORWARD + 1):
                shown_dates.append(self.selected_date + timedelta(days=delta))

            for i, date in enumerate(shown_dates):
                attrb = curses.A_BOLD if date == self.today else curses.A_NORMAL
                formatted_date = date.strftime(PRETTY_DATE_FORMAT)
                header_pad.addstr(
                    1, NAME_CUTOFF + DATE_PADDING * i, formatted_date, attrb
                )

            # Add habits to pad
            for row, habit in enumerate(self.tui_habits):
                name = habit.get_name()

                if habit.get_file():
                    name = "[f] " + name

                if len(name) > (last_vis_char := NAME_CUTOFF - 2):
                    name = name[:last_vis_char] + NAME_CUTOFF_CHAR

                attrb = curses.A_BOLD
                for i, date in enumerate(shown_dates):
                    habits_pad.addstr(row, 0, name)

                    if status := habit.log.get_status(date):
                        text = f"[{STATUSES_DISPLAY[status]}]"
                        due = False

                    elif due := habit.is_due(date):
                        text = "[ ]"

                    else:
                        text = "[o]"

                    if (
                        self.options.get("hide_completed")
                        and not due
                        and date == self.selected_date
                    ):
                        attrb = curses.A_DIM
                    habits_pad.addstr(row, NAME_CUTOFF + DATE_PADDING * i, text)
                habits_pad.chgat(row, 0, attrb)

            attrb = curses.A_STANDOUT
            if bool(habits_pad.inch(self.selected_habit_nr, 0) & curses.A_BOLD):
                attrb = attrb | curses.A_BOLD
            habits_pad.chgat(self.selected_habit_nr, 0, attrb)

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
