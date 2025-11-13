import sys
import time
from functools import wraps
from rich.text import Text
from rich.live import Live
from rich.console import Console
from rich.spinner import Spinner
from rich.table import Table
from namecheck.render.const import PINK, INDENT

def clear_previous_lines(lines: int = 1, immediate: bool = False, sleep_time: float = 0.1):
    """Moves cursor up N lines and clears them."""
    for _ in range(lines):
        if lines > 1 and not immediate: 
            time.sleep(sleep_time)
        # Moves cursor up one line
        print("\x1b[1A", end="", flush=True)
        # Clears the entire line
        print("\x1b[2K", end="", flush=True)

def spinner(message: str, indent: bool = True):
    """Decorator to show a spinner while a function is running."""
    def decorator(func: callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            indent_text = Text(INDENT)
            spinner_obj = Spinner("dots", text=Text.from_markup(message), style=PINK)
            render_table = Table.grid()
            render_table.add_row(indent_text, spinner_obj)

            # Create an update function
            def update_spinner_text(new_message: str):
                spinner_obj.update(text=Text.from_markup(new_message))
                new_table = Table.grid()
                new_table.add_row(indent_text, spinner_obj)
                live.update(new_table)

            with Live(render_table, refresh_per_second=10, transient=True) as live:
                # Inject the update function into kwargs
                kwargs['update_spinner'] = update_spinner_text
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator