import sys
import difflib
import requests
from bs4 import BeautifulSoup
from collections import defaultdict

# URLs for the simple package indexes
SOURCES = {
    'PyPI': 'https://pypi.org/',
    'TestPyPI': 'https://test.pypi.org/'
}

def get_all_package_names():
    """
    Fetches and parses package names from the given source URLs.
    Returns a dictionary mapping package names to a set of their sources.
    """
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
            
    print(f"\nFound {len(package_names)} unique package names across all sources.", file=sys.stderr)
    return dict(package_names)

def get_sources_for_name(name, all_names_with_sources) -> str:
    """
    Returns the sources for a given name.
    """
    normalized_name = name.lower()
    sources = sorted(list(all_names_with_sources[normalized_name]))
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
        project_url = f"{url}/project/{name}/"
        response = requests.get(project_url, timeout=30)
        if response.status_code == 200:
            sources.append(source_name)
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

def check_name_availability(name, all_names_with_sources):
    """
    Checks for an exact match and finds close matches, showing their sources.
    """
    print("-" * 50)
    
    ## check for exact match in the global index
    exact_match = is_name_taken_global_index(name, all_names_with_sources)
    if exact_match:
        sources = get_sources_for_name(name, all_names_with_sources)
        print_taken(name, sources)
    else:
        ## in this case, it _could_ mean the name is available, but
        ## the cachec might be outdated, so lets do a direct url check
        ## to make sure
        is_taken = is_name_taken_project_url(name)
        if is_taken:
            sources = is_taken
            print_taken(name, is_taken)
        else:
            print_available(name)
    
    close_matches = get_close_matches(name, all_names_with_sources)
    ## if there are close matches, display them
    if close_matches:
        print_matches(close_matches, all_names_with_sources)
            
    print("-" * 50)



## --- print output functions ---
def print_available(name: str):
    print(f"✅ The name '{name}' appears to be available!")

def print_taken(name: str, source: list[str]):
    sources = ", ".join(sorted(source))
    print(f"❌ Exact match for '{name}' found on: {sources}")

def print_matches(matches: list[str], all_names_with_sources: dict[str, set[str]]):
    print("\n⚠️  Found closely matching package names:")
    for match in matches:
        sources = ", ".join(sorted(list(all_names_with_sources[match])))
        print(f"   - {match} (on: {sources})")
