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


class _Pad:
    def __init__(self) -> None:
        self.pad: curses.window
        self.contents: list[tuple[str, int]] = []

    def add_str(
        self, content: str, attr: int = curses.A_NORMAL, padding: int = 0
    ) -> None:
        self.contents.append((content.rjust(padding), attr))

    def get_height(self) -> int:
        return len(self.contents)

    def get_width(self) -> int:
        return max(len(content) for content, _ in self.contents)

    def refresh(self, pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol):
        self.pad = curses.newpad(self.get_height() + 1, self.get_width() + 1)
        for row, content in enumerate(self.contents):
            self.pad.addstr(row, 0, content[0], content[1])
        self.pad.refresh(pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol)

    def __repr__(self) -> str:
        return "\n".join(c[0] for c in self.contents)


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
        def _format_name(habit: Habit) -> str:
            name = habit.get_name()

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
            for row, habit in enumerate(self.tui_habits):
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

                if row == self.selected_habit_nr:
                    attr |= curses.A_STANDOUT

                habits_pad.add_str(habit_row, attr=attr)

            # Refresh all pads at once.
            curses.update_lines_cols()  # detect screen resize
            y_max, x_max = [p - 1 for p in stdscr.getmaxyx()]

            header_bottom = header_pad.get_height() - 1
            scroll = max(0, self.selected_habit_nr - y_max + header_bottom)
            header_pad.refresh(0, 0, 0, 0, header_bottom, x_max)
            habits_pad.refresh(scroll, 0, header_bottom + 1, 0, y_max, x_max)

            if (key := stdscr.getkey()) in self.keybinds:
                self.keybinds[key](stdscr)
            else:
                print(key)
