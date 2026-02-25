#!/usr/bin/env python3
"""
Scrape game/app listings from twilight-cd.com for releases that are missing
data or have bad data (numbered folder names instead of real names).

Saves results to tools/scraped_data.json for use by build_website.py.
"""

import json
import re
import time
import sys
from pathlib import Path
from html import unescape

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

SCRIPT_DIR = Path(__file__).parent
OUTPUT = SCRIPT_DIR / "scraped_data.json"

# URL map for releases we need data for.
# Built from the twilight-cd.com/releases/ index page.
# For each release, try DVD URL first, then CD URL(s).
RELEASE_URLS = {
    2: [
        "http://twilight-cd.com/releases/1996-2/twilight-002-0996002-dutch-edition/",
    ],
    10: [
        "http://twilight-cd.com/releases/1997-2/twilight-010-0497010-dutch-edition/",
    ],
    11: [
        "http://twilight-cd.com/releases/1997-2/twilight-011-0597011-dutch-edition/",
    ],
    12: [
        "http://twilight-cd.com/releases/1997-2/twilight-012-0697012-dutch-edition/",
    ],
    14: [
        "http://twilight-cd.com/releases/1997-2/twilight-014-0897014-dutch-edition/",
    ],
    43: [
        "http://twilight-cd.com/releases/1999-2/twilight-043-1099043/",
    ],
    44: [
        "http://twilight-cd.com/releases/2000-2/twilight-044-0100044/",
    ],
    45: [
        "http://twilight-cd.com/releases/2000-2/twilight-045-0200045/",
    ],
    47: [
        "http://twilight-cd.com/releases/2000-2/twilight-047-0200047/",
    ],
    49: [
        "http://twilight-cd.com/releases/2000-2/twilight-049-dvd/",
        "http://twilight-cd.com/releases/2000-2/twilight-049-2cd-0200049/",
    ],
    50: [
        "http://twilight-cd.com/releases/2000-2/twilight-050-2cd-0200050/",
    ],
    51: [
        "http://twilight-cd.com/releases/2000-2/twilight-051-dvd/",
    ],
    52: [
        "http://twilight-cd.com/releases/2000-2/twilight-052-dvd/",
    ],
    53: [
        "http://twilight-cd.com/releases/2000-2/twilight-053-dvd/",
    ],
    54: [
        "http://twilight-cd.com/releases/2000-2/twilight-054-dvd/",
        "http://twilight-cd.com/releases/2000-2/twilight-054-2cd-0200054/",
    ],
    55: [
        "http://twilight-cd.com/releases/2000-2/twilight-055-dvd/",
    ],
    57: [
        "http://twilight-cd.com/releases/2001-2/twilight-057-dvd/",
    ],
    62: [
        "http://twilight-cd.com/releases/2001-2/twilight-062-dvd/",
    ],
    65: [
        "http://twilight-cd.com/releases/2001-2/twilight-065-dvd/",
    ],
    67: [
        "http://twilight-cd.com/releases/2001-2/twilight-067-dvd/",
    ],
    69: [
        "http://twilight-cd.com/releases/2002-2/twilight-069-dvd/",
    ],
    70: [
        "http://twilight-cd.com/releases/2002-2/twilight-070-dv/",
        "http://twilight-cd.com/releases/2002-2/twilight-070-dvd/",
    ],
    72: [
        "http://twilight-cd.com/releases/2002-2/twilight-072-dvd/",
    ],
    73: [
        "http://twilight-cd.com/releases/2002-2/twilight-073-dvd/",
    ],
    74: [
        "http://twilight-cd.com/releases/2002-2/twilight-074-dvd/",
    ],
    75: [
        "http://twilight-cd.com/releases/2002-2/twilight-075-dvd/",
    ],
    76: [
        "http://twilight-cd.com/releases/2002-2/twilight-076-dvd/",
    ],
    78: [
        "http://twilight-cd.com/releases/2002-2/twilight-078-dvd/",
    ],
    79: [
        "http://twilight-cd.com/releases/2002-2/twilight-079-dvd/",
    ],
    # BAD GAMES releases (numbered folder names instead of real names)
    80: [
        "http://twilight-cd.com/releases/2003-2/twilight-080-dvd/",
    ],
    81: [
        "http://twilight-cd.com/releases/2003-2/twilight-081-dvd/",
    ],
    82: [
        "http://twilight-cd.com/releases/2003-2/twilight-082-dvd/",
    ],
    83: [
        "http://twilight-cd.com/releases/2003-2/twilight-083-dvd/",
    ],
    84: [
        "http://twilight-cd.com/releases/2003-2/twilight-084-dvd/",
    ],
    85: [
        "http://twilight-cd.com/releases/2003-2/twilight-085-dvd/",
    ],
    86: [
        "http://twilight-cd.com/releases/2003-2/twilight-086-dvd/",
    ],
    87: [
        "http://twilight-cd.com/releases/2003-2/twilight-087-2dvd/",
    ],
}


def fetch_url(url: str) -> str | None:
    """Fetch a URL and return the HTML content."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Twilight-ISO-Indexer/1.0',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"  FAIL: {url} -> {e}")
        return None


def clean_text(text: str) -> str:
    """Clean HTML entities and extra whitespace from text."""
    text = unescape(text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    text = text.strip()
    # Normalize dashes
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    return text


def parse_release_page(html: str) -> dict | None:
    """Parse a twilight-cd.com release page for [Games] and [Apps] lists.
    
    The HTML structure uses:
    - <h3>[Games]</h3> or <h2>Games</h2> etc followed by <ul><li>items</li></ul>
    - <h3>[Apps]</h3> or similar followed by <ul><li>items</li></ul>
    - Sometimes <h2>List.txt</h2> with a <pre> block containing text format
    """
    games = []
    apps = []

    # Strategy 1: Look for [Games] and [Apps] sections with <ul><li>
    # Find all h2/h3 headers and the HTML following them
    sections = re.split(r'<h[23][^>]*>', html)
    
    for i, section in enumerate(sections):
        # Check if this section header indicates Games or Apps  
        header_match = re.match(r'([^<]*)</h[23]>', section)
        if not header_match:
            continue
        header = clean_text(header_match.group(1)).lower().strip('[] ')
        
        is_games = header in ('games', 'game', '[games]')
        is_apps = header in ('apps', 'app', 'applications', 'prowares', '[apps]')
        
        if not is_games and not is_apps:
            continue
        
        # Extract <li> items from the first <ul> after this header
        rest = section[header_match.end():]
        ul_match = re.search(r'<ul[^>]*>(.*?)</ul>', rest, re.DOTALL)
        if not ul_match:
            continue
        
        items = re.findall(r'<li[^>]*>(.*?)</li>', ul_match.group(1), re.DOTALL)
        cleaned = [clean_text(item) for item in items if clean_text(item)]
        
        # Filter out noise like "---- Runtime ----"
        cleaned = [c for c in cleaned if not re.match(r'^[-─—=]+\s*\w+\s*[-─—=]+$', c) and len(c) > 1]
        
        if is_games:
            games.extend(cleaned)
        else:
            apps.extend(cleaned)
    
    # Strategy 2: If no structured lists found, try parsing <pre> block (List.txt)
    if not games and not apps:
        pre_match = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.DOTALL)
        if pre_match:
            pre_text = clean_text(pre_match.group(1))
            current_section = None
            for line in pre_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                lower = line.lower().strip('[] ')
                if lower in ('games', 'game'):
                    current_section = 'games'
                    continue
                elif lower in ('apps', 'app', 'applications', 'prowares'):
                    current_section = 'apps'
                    continue
                
                # Skip ASCII art and noise
                alphanum = sum(1 for c in line if c.isalnum() and ord(c) < 127)
                if len(line) > 3 and alphanum < len(line) * 0.3:
                    continue
                if re.match(r'^[-─—=*_\s]+$', line):
                    continue
                if 'Release' in line and re.search(r'Release\s+\d+', line):
                    continue
                
                if current_section == 'games' and len(line) > 1:
                    games.append(line)
                elif current_section == 'apps' and len(line) > 1:
                    apps.append(line)
    
    if not games and not apps:
        return None
    
    return {'games': games, 'apps': apps}


def main():
    print(f"Scraping {len(RELEASE_URLS)} releases from twilight-cd.com...")
    results = {}
    success = 0
    failed = 0
    
    for num in sorted(RELEASE_URLS.keys()):
        urls = RELEASE_URLS[num]
        print(f"\nRelease {num:03d}:", end=" ")
        
        data = None
        for url in urls:
            html = fetch_url(url)
            if html:
                data = parse_release_page(html)
                if data:
                    print(f"OK ({len(data['games'])} games, {len(data['apps'])} apps) <- {url}")
                    break
                else:
                    print(f"  No game/app data found at {url}")
            
            time.sleep(0.5)  # Be polite
        
        if data:
            results[str(num)] = data
            success += 1
        else:
            print(f"FAILED - no data found")
            failed += 1
        
        time.sleep(0.5)  # Be polite
    
    # Save results
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Results: {success} scraped, {failed} failed")
    print(f"Saved to {OUTPUT}")
    
    # Show summary
    total_games = sum(len(d['games']) for d in results.values())
    total_apps = sum(len(d['apps']) for d in results.values())
    print(f"Total: {total_games} games, {total_apps} apps across {len(results)} releases")


if __name__ == '__main__':
    main()
