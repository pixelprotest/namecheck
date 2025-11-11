import sys
from namecheck.render.const import PURPLE, PINK
from namecheck.utils import (get_all_package_names, 
                             render_name_availability,
                             get_name_availability)
from rich.console import Console
from rich.prompt import Prompt, Confirm
from namecheck.render.utils import clear_previous_lines, print_text

console = Console()

def main():
    """
    Main function to run the package name checker.
    """
    all_package_names = get_all_package_names()
    if not all_package_names:
        print("Could not retrieve any package names. Exiting.", file=sys.stderr)
        return

    while True:
        try:
            console.clear()
            console.print(f"[bold]Enter a package name to check. Type [bold {PINK}]'q'[/] or [bold {PINK}]'exit'[/] to quit.[/]")
            check_another_name = False
            # user_input = input("\n> Check name: ")
            user_input = Prompt.ask(f"\n[bold]> Check name[/]", console=console)
            if user_input.lower() in ['q', 'exit']:
                break
            if user_input:
                clear_previous_lines(3)
                print_text(f"Name availability for '{user_input}'", console=console)
                is_available, taken_sources, close_matches = get_name_availability(user_input, all_package_names)
                render_name_availability(user_input, 
                                         is_available, 
                                         taken_sources, 
                                         close_matches, 
                                         all_package_names, 
                                         console=console)
                # check_name_availability(user_input, all_package_names)
                check_another_name = Confirm.ask(f"\n[bold]Do you want to check another name?[/]", console=console)
                if check_another_name:
                    continue
                else:
                    break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()