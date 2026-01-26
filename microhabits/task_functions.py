import os
import subprocess


def open_in_editor(file_path: str, editor=None):
    if file_path:
        if not editor:
            editor = os.getenv("EDITOR", "vi")
        file_path = os.path.expanduser(file_path)
        subprocess.run([editor, file_path], check=False)
