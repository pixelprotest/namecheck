import sys
from rich.style import Style
from rich.prompt import Prompt
from rich.console import Console
from namecheck.render.const import PINK, BLUE
from namecheck.utils import (get_all_package_names, 
                             render_name_availability,
                             get_name_availability)
from namecheck.render.utils import clear_previous_lines

console = Console()
basic_style = Style(color=BLUE, blink=False, bold=False)

def main():
    """
    Main function to run the package name checker.
    """
    console.clear()
    all_package_names = get_all_package_names()
    if not all_package_names:
        print("Could not retrieve any package names. Exiting.", file=sys.stderr)
        return

    run_count = 0
    while True:
        try:
            if run_count == 0:
                msg = f"Enter a package name to check. Type [bold {PINK}]'q'[/] or [bold {PINK}]'exit'[/] to quit."
                console.print(msg, style=basic_style)
                package_prompt_msg = f"\n[{BLUE}]package name[/]"
                user_input = Prompt.ask(package_prompt_msg, console=console)

            if user_input.lower() in ['q', 'exit']:
                break

            if user_input:
                if run_count == 0:
                    clear_previous_lines(3)
                else:
                    clear_previous_lines(1)
                
                ## check for the name availability
                console.print(f"Name availability for '{user_input}'", style=basic_style)
                is_available, taken_sources, close_matches = get_name_availability(user_input, all_package_names)
                ## now render the results
                clear_previous_lines(2)
                render_name_availability(user_input, 
                                         is_available, 
                                         taken_sources, 
                                         close_matches, 
                                         all_package_names, 
                                         console=console)
                ## offer user to check another name
                user_input = Prompt.ask(package_prompt_msg, console=console)
                if user_input:
                    lines_to_clear = len(close_matches) + 5 
                    clear_previous_lines(lines_to_clear, sleep_time=0.05)
                    run_count += 1
                    continue
                else:
                    break
        except (KeyboardInterrupt, EOFError):
            console.print("\nExiting.", style=basic_style)
            break

if __name__ == "__main__":
    main()