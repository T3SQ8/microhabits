"""Helpers for managing and loading options"""

from os import PathLike
from typing import Any, Self, TypedDict

import yaml


class Options(TypedDict):
    """Typed mapping of supported configuration options."""

    hide_completed: bool
    name_cutoff: int
    name_cutoff_char: str
    date_padding: int
    days_back: int
    days_forward: int
    header_height: int
    pretty_date_format: str
    show_alias: bool
    scroll_margin: int


DEFAULT_OPTIONS: Options = {
    "hide_completed": False,
    "name_cutoff": 25,
    "name_cutoff_char": "…",
    "date_padding": 14,
    "days_back": 1,
    "days_forward": 1,
    "header_height": 2,
    "pretty_date_format": "%d/%m (%a)",
    "show_alias": False,
    "scroll_margin": 3,
}


class OptionsManager:
    """Manages options loaded from defaults and config files."""

    def __init__(self) -> None:
        """Initialize the default values."""
        self.options: Options = DEFAULT_OPTIONS

    def load_conf_file(self, opt_file: str | PathLike) -> Self:
        """Load options from a YAML file."""
        with open(opt_file, "r", encoding="utf-8") as f:
            for k, v in yaml.safe_load(f).items():
                if k not in self.options:
                    raise ValueError(
                        f'non-valid config "{k}" specified in "{opt_file}"'
                    )
                self.options[k] = v
        return self

    def toggle_option(self, k: str) -> None:
        """Toggle a boolean option by key."""
        v = self.options[k]
        if isinstance(v, bool):
            self.options[k] = not v
        else:
            raise ValueError(f'trying to toggle non-boolean option "{k}"')

    def get(self, k: str) -> Any:
        """Return the value for a single option key."""
        return self.options[k]
