import sys
import time
from functools import wraps

from rich.console import Console, Group
from rich.text import Text
from rich.spinner import Spinner
from rich.table import Table
from rich.console import Group
from rich.live import Live
from namecheck.render.const import PINK, PURPLE, CHECK, CROSS, CLEAR_SLEEP, INDENT

def clear_previous_lines(lines: int = 1, immediate: bool = False):
    """Moves cursor up N lines and clears them."""
    for _ in range(lines):
        if lines > 1 and not immediate: 
            time.sleep(CLEAR_SLEEP)
        # Moves cursor up one line
        print("\x1b[1A", end="", flush=True)
        # Clears the entire line
        print("\x1b[2K", end="", flush=True)


def show_spinner(message: str, seconds: float = 3.0, indent: bool = True):
    """Shows a spinner for a given duration, updating the message every second."""
    indent = Text(INDENT)
    spinner = Spinner("dots", text=Text.from_markup(message), style=PINK)

    render_table = Table.grid()
    render_table.add_row(indent, spinner)

    with Live(render_table, refresh_per_second=10, transient=True):
        if seconds < 1.0:
            time.sleep(seconds)
        else:
            for i in range(int(seconds)):
                time.sleep(1)
                # Calculate the number of dots to show (1, 2, or 3, then repeat)
                num_dots = (i % 3) + 1
                dots = "." * num_dots
                spinner.text = f"{message}{dots}"


def spinner(message: str, indent: bool = True):
    """Decorator to show a spinner while a function is running."""
    def decorator(func: callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            indent = Text(INDENT)
            spinner_obj = Spinner("dots", text=Text.from_markup(message), style=PINK)
            render_table = Table.grid()
            render_table.add_row(indent, spinner_obj)

            with Live(render_table, refresh_per_second=10, transient=True):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


def print_text(text: str, console: Console, color: str = "blue1", bold: bool = False, indent: bool = False):
    """
    suggested colors are 'blue1' and 'orchid2'
    """
    if color:
        text = f"[{color}]{text}[/]"
        if bold:
            text = f"[bold {color}]{text}[/]"
    else:
        text = f"{text}"
        if bold: 
            text = f"[bold]{text}[/]"

    if indent:
        text = f"{INDENT}{text}"

    console.print(text)
