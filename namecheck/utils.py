import sys
import difflib
import requests
from bs4 import BeautifulSoup
from collections import defaultdict

def get_all_package_names(sources):
    """
    Fetches and parses package names from the given source URLs.
    Returns a dictionary mapping package names to a set of their sources.
    """
    package_names = defaultdict(set)
    for source_name, url in sources.items():
        try:
            print(f"Fetching package list from {source_name} ({url})...", file=sys.stderr)
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all anchor tags and extract their text
            for link in soup.find_all('a'):
                name = link.get_text().lower()
                package_names[name].add(source_name)
                
        except requests.RequestException as e:
            print(f"Error fetching data from {url}: {e}", file=sys.stderr)
            
    print(f"\nFound {len(package_names)} unique package names across all sources.", file=sys.stderr)
    return dict(package_names)



def check_name_availability(name, all_names_with_sources):
    """
    Checks for an exact match and finds close matches, showing their sources.
    """
    normalized_name = name.lower()
    
    print("-" * 50)
    
    # Check for an exact match
    if normalized_name in all_names_with_sources:
        sources = ", ".join(sorted(list(all_names_with_sources[normalized_name])))
        print(f"❌ Exact match for '{name}' found on: {sources}.")
    else:
        print(f"✅ The name '{name}' appears to be available!")

    # Find and display close matches
    close_matches = difflib.get_close_matches(
        normalized_name, all_names_with_sources.keys(), n=5, cutoff=0.8
    )
    
    # If the exact name was found, remove it from the "close matches" list to avoid redundancy.
    if normalized_name in close_matches:
        close_matches.remove(normalized_name)
        
    if close_matches:
        print("\n⚠️  Found closely matching package names:")
        for match in close_matches:
            sources = ", ".join(sorted(list(all_names_with_sources[match])))
            print(f"   - {match} (on: {sources})")
            
    print("-" * 50)
