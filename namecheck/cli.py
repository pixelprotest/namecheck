import sys
from namecheck.utils import (get_all_package_names, 
                              check_name_availability)


def main():
    """
    Main function to run the package name checker.
    """
    all_package_names = get_all_package_names()
    
    if not all_package_names:
        print("Could not retrieve any package names. Exiting.", file=sys.stderr)
        return

    print("\nEnter a package name to check. Type 'q' or 'exit' to quit.")
    
    while True:
        try:
            user_input = input("\n> Check name: ")
            if user_input.lower() in ['q', 'exit']:
                break
            if user_input:
                check_name_availability(user_input, all_package_names)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()