"""Helpers for managing and loading options"""

from pathlib import Path
from typing import Any, Self

import yaml

DEFAULT_OPTIONS = {
    "hide_completed": False,
    "name_cutoff": 25,
    "name_cutoff_char": "…",
    "date_padding": 14,
    "days_back": 1,
    "days_forward": 1,
    "header_height": 2,
    "pretty_date_format": "%d/%m (%a)",
}


class OptionsManager:
    """Manages options loaded from defaults and config files."""

    def __init__(self) -> None:
        """Initialize the default values."""
        self.options: dict[str, Any] = DEFAULT_OPTIONS

    def load_conf_file(self, opt_file: Path) -> Self:
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

    def get(self, k: str):
        """Return the value for a single option key."""
        return self.options[k]
