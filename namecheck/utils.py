import os
import sys
import time
import pickle
import difflib
import requests
from rich.console import Console
from bs4 import BeautifulSoup
from collections import defaultdict
from platformdirs import user_cache_dir
from namecheck.render.utils import spinner
from namecheck.render.const import GREEN, RED, ORANGE, BLUE
from rich.style import Style

# URLs for the simple package indexes
SOURCES = {
    'PyPI': 'https://pypi.org/',
    'TestPyPI': 'https://test.pypi.org/'
}

basic_style = Style(color=BLUE, blink=False, bold=False)
blink_style = Style(color=BLUE, blink=True, bold=False)

def load_package_names_from_cache():
    """
    Loads the package names from the cache.
    """
    cache_dir = user_cache_dir('namecheck')
    cache_file = os.path.join(cache_dir, 'package_names.pkl')
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
        try:
            with open(cache_file, 'rb') as f:
                package_names = pickle.load(f)
            # Convert defaultdict to regular dict to prevent auto-creation of keys
            return dict(package_names)
        except (pickle.UnpicklingError, EOFError, ValueError) as e:
            # Cache file is corrupted, ignore it and return None
            print(f"Warning: Cache file is corrupted, will refresh from source.", file=sys.stderr)
            return None
    return None

def save_package_names_to_cache(package_names):
    """
    Saves the package names to the cache.
    """
    cache_dir = user_cache_dir('namecheck')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, 'package_names.pkl')
    with open(cache_file, 'wb') as f:
        pickle.dump(package_names, f)

def get_all_package_names():
    """
    Fetches and parses package names from the given source URLs.
    Returns a dictionary mapping package names to a set of their sources.
    """
    ## check if the package names are already in the cache
    package_names = load_package_names_from_cache()
    if package_names:
        return dict(package_names)

    package_names = defaultdict(set)
    for source_name, url in SOURCES.items():
        index_url = url + 'simple/'
        try:
            print(f"Fetching package list from {source_name} ({index_url})...", file=sys.stderr)
            response = requests.get(index_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all anchor tags and extract their text
            for link in soup.find_all('a'):
                name = link.get_text().lower()
                package_names[name].add(source_name)
                
        except requests.RequestException as e:
            print(f"Error fetching data from {index_url}: {e}", file=sys.stderr)

    ## save the package names to the cache
    save_package_names_to_cache(package_names)

    print(f"\nFound {len(package_names)} unique package names across all sources.", file=sys.stderr)
    return dict(package_names)

def get_sources_for_name(name, all_names_with_sources) -> str:
    """
    Returns the sources for a given name.
    """
    normalized_name = name.lower()
    # Use .get() with default empty set to avoid KeyError
    sources = sorted(list(all_names_with_sources.get(normalized_name, set())))
    # sources = sorted(list(all_names_with_sources[normalized_name]))
    return sources

def is_name_taken_global_index(name, all_names_with_sources) -> bool:
    """
    Checks the global index for a given name
    Gives better overview, but might be cached and outdated.
    """
    normalized_name = name.lower()
    found = True if normalized_name in all_names_with_sources else False
    return found

def is_name_taken_project_url(name) -> list:
    """
    Instead of checking the global index, we check the project URL directly.
    Only used as a secondary check to make sure the name _is_ really available, 
    not just available in the cached global index.
    returns a list of sources where the name is taken
    """
    sources = []
    for source_name, url in SOURCES.items():
        project_url = f"{url}project/{name}/"
        try:
            response = requests.get(project_url, timeout=30)
            if response.status_code == 200:
                # PyPI returns 200 even for non-existent packages
                # Look for indicators that the package actually exists
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check if the error message is present
                page_text = soup.get_text().lower()
                if "couldn't find this page" in page_text or "not found" in page_text:
                    # Package doesn't exist
                    continue
                
                # Look for positive indicators (like package description, download buttons, etc.)
                # PyPI has specific elements for real package pages
                if soup.find('div', class_='package-header') or soup.find('div', class_='project-description'):
                    sources.append(source_name)
        except requests.RequestException as e:
            # If there's a network error, we can't determine if it's taken
            print(f"Warning: Could not check {source_name} for '{name}': {e}", file=sys.stderr)
    return sources
    
def get_close_matches(name, all_names_with_sources) -> list:
    """
    Returns a list of close matches for a given name.
    """
    name_norm = name.lower()
    # Find and display close matches
    matches = difflib.get_close_matches(name_norm, 
                                        all_names_with_sources.keys(), 
                                        n=5, 
                                        cutoff=0.8)
    ## if the exact name was found, remove it from 
    ## the "matches" list to avoid redundancy.
    if name_norm in matches:
        matches.remove(name_norm)
    return matches

@spinner("Checking...")
def get_name_availability(name, all_names_with_sources) -> tuple[bool, list[str], list[str]]:
    """
    Checks for an exact match and finds close matches, showing their sources.
    """
    time.sleep(0.5)
    is_available = None
    taken_sources = []
    close_matches = []

    ## check for exact match in the global index
    exact_match = is_name_taken_global_index(name, all_names_with_sources)
    if exact_match:
        sources = get_sources_for_name(name, all_names_with_sources)
        is_available = False
        taken_sources = sources
    else:
        ## in this case, it _could_ mean the name is available, but
        ## the cachec might be outdated, so lets do a direct url check
        ## to make sure
        is_taken = is_name_taken_project_url(name)
        if is_taken:
            is_available = False
            taken_sources = is_taken
        else:
            is_available = True
            taken_sources = []
    
    matches = get_close_matches(name, all_names_with_sources)
    ## if there are close matches, display them
    if matches:
        close_matches = matches

    return is_available, taken_sources, close_matches

def render_name_availability(name, is_available, taken_sources, close_matches, all_names_with_sources, console: Console):
    if is_available:
        print_available(name, console)
    else:
        print_taken(name, taken_sources, console)

    if close_matches:
        print_matches(close_matches, all_names_with_sources, console)


## --- print output functions ---
def print_available(name: str, console: Console):
    console.print(f"The name [bold {GREEN}]'{name}'[/] appears to be [bold {GREEN}]available![/]", style=blink_style)

def print_taken(name: str, sources: list[str], console: Console):
    sources_w_color = [f"[bold {RED}]{x}[/]" for x in sources]
    sources_str = ", ".join(sorted(sources_w_color))
    console.print(f"The name [bold {RED}]'{name}'[/] is already taken on: {sources_str}", style=basic_style)

def print_matches(matches: list[str], all_names_with_sources: dict[str, set[str]], console: Console):
    console.print("\nFound closely matching package names:", style=basic_style)
    for match in matches:
        sources = [f"[{ORANGE}]{source}[/]" for source in sorted(list(all_names_with_sources[match]))]
        sources = ", ".join(sources)
        console.print(f"   - [bold {ORANGE}]{match}[/] (on: {sources})", style=basic_style)
