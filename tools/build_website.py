#!/usr/bin/env python3
"""
Parse all Twilight disc data sources and generate a static searchable website.

Data sources (in priority order):
1. list_txt_files/*/MENU/LIST.TXT  - local disc menus (games + apps, best data)
2. twilight_games_list.txt          - scraped games list (games only)
3. scraped_data.json                - scraped from twilight-cd.com (fills gaps & fixes bad data)
"""

import json
import os
import re
import glob
from pathlib import Path
from collections import OrderedDict
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "downloads"
LIST_TXT_DIR = DATA_DIR / "list_txt_files"
GAMES_LIST = DATA_DIR / "twilight_games_list.txt"
OUTPUT_DIR = PROJECT_ROOT / "docs"

SCRAPED_DATA = SCRIPT_DIR / "scraped_data.json"
ARCHIVE_BASE = "https://archive.org/download/twilight-warez-cd-pack-1-tm-89/"


def normalize_disc_key(name: str) -> tuple:
    """Convert disc name to (release_number, disc_letter_or_empty).
    e.g. 'Twilight28a' -> (28, 'a'), 'Twilight004' -> (4, '')
    """
    m = re.match(r'[Tt]wilight0*(\d+)([aAbB]?)', name)
    if not m:
        return (0, '')
    return (int(m.group(1)), m.group(2).lower())


def parse_list_txt(filepath: str) -> dict:
    """Parse a LIST.TXT file into games and apps lists."""
    try:
        # Try multiple encodings
        content = None
        for enc in ('cp437', 'latin-1', 'utf-8'):
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if not content or len(content.strip()) < 10:
            return None
    except Exception:
        return None

    # Find release number
    release_match = re.search(r'Release\s+(\d+)', content)
    release_num = int(release_match.group(1)) if release_match else 0

    games = []
    apps = []
    current_section = None

    for line in content.split('\n'):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue
        # Skip lines that are mostly non-ASCII (ASCII art banners)
        ascii_alphanum = sum(1 for c in line if c.isalnum() and ord(c) < 127)
        if len(line) > 3 and ascii_alphanum < len(line) * 0.3:
            continue
        # Skip pure decoration lines
        if all(c in '═─━┌┐└┘│┬┴├┤╔╗╚╝║╠╣╦╩╬-=*_ ' or ord(c) > 127 for c in line):
            continue
        if re.match(r'^[\s\-=*_]+$', line):
            continue
        if 'Release' in line and release_match:
            continue
        if 'will be released' in line.lower():
            continue

        # Section headers
        lower = line.lower().strip('[] ')
        if lower in ('games', 'game'):
            current_section = 'games'
            continue
        elif lower in ('apps', 'app', 'applications', 'prowares'):
            current_section = 'apps'
            continue
        elif line.startswith('[') and line.endswith(']'):
            current_section = 'apps' if 'app' in lower or 'pro' in lower else 'games'
            continue

        if current_section and len(line) > 1:
            # Filter out noise
            if line.startswith('+') or line.startswith('             '):
                continue
            entry = line.strip()
            if current_section == 'games':
                games.append(entry)
            else:
                apps.append(entry)

    if not games and not apps:
        # For release 1, there are no section headers - split by "Abode Acrobat"/"Adobe Acrobat" line
        def is_content_line(l):
            l = l.strip()
            if not l or len(l) < 2:
                return False
            # Filter ASCII art: lines with low ratio of ASCII alphanumeric chars
            alphanum = sum(1 for c in l if c.isalnum() and ord(c) < 127)
            if len(l) > 3 and alphanum < len(l) * 0.3:
                return False
            if all(c in '═─━┌┐└┘│┬┴├┤╔╗╚╝║╠╣╦╩╬-=*_ ' or ord(c) > 127 for c in l):
                return False
            if re.match(r'^[\s\-=*_]+$', l):
                return False
            return True

        lines = [l.strip() for l in content.split('\n') if is_content_line(l)]
        # Find transition point (first Adobe/Abode entry)
        split_idx = None
        for i, l in enumerate(lines):
            if l.startswith('Abode') or (l.startswith('Adobe') and i > 5):
                split_idx = i
                break
        if split_idx:
            games = lines[:split_idx]
            apps = lines[split_idx:]
        else:
            games = lines

    return {'games': games, 'apps': apps, 'release': release_num}


def parse_games_list(filepath: str) -> dict:
    """Parse twilight_games_list.txt into a dict of disc -> games list."""
    result = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by release headers
    sections = re.split(r'={3,}\n(Twilight\w+)\n={3,}', content)
    # sections: ['', 'Twilight001', '\n\n...', 'Twilight002', ...]
    for i in range(1, len(sections), 2):
        disc_name = sections[i].strip()
        games_text = sections[i + 1].strip() if i + 1 < len(sections) else ''
        games = [g.strip() for g in games_text.split('\n') if g.strip()]
        if games:
            result[disc_name] = games

    return result


def find_cover_images() -> dict:
    """Scan for cover JPG files and map release_num -> list of cover info."""
    covers = {}
    for jpg in sorted(DATA_DIR.glob("TWILIGHT *.jpg")):
        name = jpg.name
        if '_thumb' in name:
            continue
        m = re.match(r'TWILIGHT\s+(\d+)\s+(CDa|CDb|DVD)\s+Cover\.jpg', name)
        if not m:
            continue
        num = int(m.group(1))
        disc_type = m.group(2)  # CDa, CDb, or DVD
        thumb_name = name.replace('.jpg', '_thumb.jpg')
        if num not in covers:
            covers[num] = []
        covers[num].append({
            'type': disc_type,
            'url': ARCHIVE_BASE + quote(name),
            'thumb': ARCHIVE_BASE + quote(thumb_name),
        })
    return covers


def find_disc_files() -> dict:
    """Scan for ISO/BIN files and map release_num -> list of file info."""
    files = {}
    for ext in ('*.iso', '*.bin'):
        for f in sorted(DATA_DIR.glob(ext)):
            name = f.name
            m = re.match(r'Twilight0*(\d+)([aAbB]?)\.(?:iso|bin)', name)
            if not m:
                continue
            num = int(m.group(1))
            letter = m.group(2).lower()
            if num not in files:
                files[num] = []
            files[num].append({
                'filename': name,
                'letter': letter,
                'url': ARCHIVE_BASE + quote(name),
            })
    return files


def has_bad_game_names(games: list) -> bool:
    """Check if game names are numbered folder names like '001', '002' etc."""
    if not games:
        return False
    numbered = sum(1 for g in games if re.match(r'^\d{2,3}$', g.strip()))
    return numbered > len(games) * 0.5


def load_scraped_data() -> dict:
    """Load scraped data from twilight-cd.com (tools/scraped_data.json)."""
    if not SCRAPED_DATA.exists():
        return {}
    with open(SCRAPED_DATA, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_index() -> dict:
    """Build the complete release index from all sources."""
    releases = {}

    # 1. Parse all LIST.TXT files
    for list_file in sorted(glob.glob(str(LIST_TXT_DIR / '*/[Mm][Ee][Nn][Uu]/LIST.TXT'))):
        path = Path(list_file)
        disc_name = path.parent.parent.name  # e.g. Twilight28a
        data = parse_list_txt(list_file)
        if data and (data['games'] or data['apps']):
            releases[disc_name] = {
                'games': data['games'],
                'apps': data['apps'],
                'source': 'list_txt'
            }

    # 2. Fill in missing releases from twilight_games_list.txt
    if GAMES_LIST.exists():
        games_data = parse_games_list(str(GAMES_LIST))
        for disc_name, games in games_data.items():
            if disc_name not in releases:
                releases[disc_name] = {
                    'games': games,
                    'apps': [],
                    'source': 'games_list'
                }

    # Group by release number, merge a/b discs
    grouped = {}
    for disc_name, data in releases.items():
        num, letter = normalize_disc_key(disc_name)
        if num == 0:
            continue
        if num not in grouped:
            grouped[num] = {
                'release': num,
                'discs': [],
                'games': [],
                'apps': [],
            }

        disc_label = f"Twilight {num}"
        if letter:
            disc_label += letter

        grouped[num]['discs'].append({
            'name': disc_name,
            'letter': letter,
        })

        # Set games/apps from first disc with data (a and b usually share the same list)
        if not grouped[num]['games'] and data['games']:
            grouped[num]['games'] = data['games']
        if not grouped[num]['apps'] and data.get('apps'):
            grouped[num]['apps'] = data['apps']

    # 3. Fill in or fix data from twilight-cd.com scraped data
    scraped = load_scraped_data()
    scraped_used = 0
    for num_str, sdata in scraped.items():
        num = int(num_str)
        if num in grouped:
            bad_games = has_bad_game_names(grouped[num]['games'])
            # Replace games if current data is empty or has bad names (numbered folders)
            if bad_games or not grouped[num]['games']:
                if sdata.get('games'):
                    grouped[num]['games'] = sdata['games']
                    scraped_used += 1
            # Replace apps if empty or if games were bad (same source, likely bad too)
            if bad_games or not grouped[num]['apps']:
                if sdata.get('apps'):
                    grouped[num]['apps'] = sdata['apps']
        else:
            # Release not yet in index - add it
            grouped[num] = {
                'release': num,
                'discs': [{'name': f'Twilight{num}', 'letter': ''}],
                'games': sdata.get('games', []),
                'apps': sdata.get('apps', []),
            }
            scraped_used += 1

    if scraped_used:
        print(f"  Scraped data: filled/fixed {scraped_used} releases from twilight-cd.com")

    # Attach cover images and disc files
    covers = find_cover_images()
    disc_files = find_disc_files()

    for num, data in grouped.items():
        data['covers'] = covers.get(num, [])
        data['files'] = disc_files.get(num, [])

    # 4. Add releases that have disc files or covers but no game/app data
    all_release_nums = set(covers.keys()) | set(disc_files.keys())
    for num in all_release_nums:
        if num not in grouped:
            # Build disc list from file names
            discs = []
            for f in disc_files.get(num, []):
                discs.append({
                    'name': f['filename'].replace('.iso', '').replace('.bin', ''),
                    'letter': f['letter'],
                })
            grouped[num] = {
                'release': num,
                'discs': discs or [{'name': f'Twilight{num}', 'letter': ''}],
                'games': [],
                'apps': [],
                'covers': covers.get(num, []),
                'files': disc_files.get(num, []),
            }

    # Sort by release number
    return OrderedDict(sorted(grouped.items()))


def generate_html(releases: dict) -> str:
    """Generate the complete HTML for the website."""
    # Count totals
    total_games = sum(len(r['games']) for r in releases.values())
    total_apps = sum(len(r['apps']) for r in releases.values())
    total_releases = len(releases)

    # Build JSON data for JS
    js_data = json.dumps(list(releases.values()), ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Twilight Warez CD Collection – Game & Software Index</title>
<meta name="description" content="Searchable index of all games and software across {total_releases} Twilight Warez CD releases (1996-2000).">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💿</text></svg>">
<style>
:root {{
  --bg: #0a0a12;
  --bg2: #12121e;
  --bg3: #1a1a2e;
  --accent: #6c63ff;
  --accent2: #ff6584;
  --text: #e0e0e8;
  --text2: #8888a0;
  --border: #2a2a40;
  --game: #4ade80;
  --app: #60a5fa;
  --highlight: #fbbf24;
  --radius: 8px;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
}}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* Header */
.header {{
  background: linear-gradient(135deg, var(--bg2) 0%, var(--bg3) 100%);
  border-bottom: 1px solid var(--border);
  padding: 2rem 1rem 1.5rem;
  text-align: center;
}}
.header h1 {{
  font-size: clamp(1.5rem, 4vw, 2.5rem);
  font-weight: 800;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 0.25rem;
}}
.header .subtitle {{
  color: var(--text2);
  font-size: 0.95rem;
}}
.stats {{
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}}
.stat {{
  text-align: center;
}}
.stat-num {{
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent);
}}
.stat-label {{
  font-size: 0.75rem;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

/* Search */
.search-container {{
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 0.75rem 1rem;
}}
.search-inner {{
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}}
.search-box {{
  flex: 1;
  min-width: 200px;
  position: relative;
}}
.search-box input {{
  width: 100%;
  padding: 0.65rem 1rem 0.65rem 2.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg2);
  color: var(--text);
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}}
.search-box input:focus {{
  border-color: var(--accent);
}}
.search-box input::placeholder {{ color: var(--text2); }}
.search-box .icon {{
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text2);
  font-size: 1rem;
  pointer-events: none;
}}
.filters {{
  display: flex;
  gap: 0.35rem;
}}
.filter-btn {{
  padding: 0.5rem 0.85rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg2);
  color: var(--text2);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}}
.filter-btn:hover {{ border-color: var(--accent); color: var(--text); }}
.filter-btn.active {{
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}}
.result-count {{
  font-size: 0.8rem;
  color: var(--text2);
  white-space: nowrap;
}}

/* Content */
.content {{
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem;
}}

/* Release cards */
.release-card {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 0.75rem;
  overflow: hidden;
  transition: border-color 0.2s;
}}
.release-card:hover {{
  border-color: var(--accent);
}}
.release-card.hidden {{
  display: none;
}}
.release-header {{
  padding: 0.75rem 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  user-select: none;
}}
.release-header:hover {{
  background: var(--bg3);
}}
.release-num {{
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--accent);
  min-width: 2.5rem;
}}
.release-title {{
  flex: 1;
}}
.release-title .name {{
  font-weight: 600;
  font-size: 1rem;
}}
.release-title .disc-info {{
  font-size: 0.75rem;
  color: var(--text2);
}}
.release-badges {{
  display: flex;
  gap: 0.35rem;
}}
.badge {{
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 600;
}}
.badge-game {{ background: rgba(74,222,128,0.15); color: var(--game); }}
.badge-app {{ background: rgba(96,165,250,0.15); color: var(--app); }}
.chevron {{
  color: var(--text2);
  transition: transform 0.2s;
  font-size: 0.8rem;
}}
.release-card.open .chevron {{
  transform: rotate(90deg);
}}
.release-body {{
  display: none;
  padding: 0 1rem 1rem;
}}
.release-card.open .release-body {{
  display: block;
}}
.section-label {{
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
  margin: 0.75rem 0 0.35rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--border);
}}
.section-label.games {{ color: var(--game); }}
.section-label.apps {{ color: var(--app); }}
.item-list {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.2rem 1rem;
}}
.item {{
  padding: 0.15rem 0;
  font-size: 0.88rem;
}}
.item .type-dot {{
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 0.35rem;
  vertical-align: middle;
}}
.type-dot.game {{ background: var(--game); }}
.type-dot.app {{ background: var(--app); }}

/* Cover images */
.covers-row {{
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}}
.cover-link {{
  display: block;
  border-radius: var(--radius);
  overflow: hidden;
  border: 2px solid var(--border);
  transition: border-color 0.2s, transform 0.2s;
  position: relative;
}}
.cover-link:hover {{
  border-color: var(--accent);
  transform: scale(1.03);
}}
.cover-link img {{
  display: block;
  height: 140px;
  width: auto;
  object-fit: contain;
  background: #000;
}}
.cover-label {{
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0,0,0,0.7);
  color: var(--text);
  font-size: 0.65rem;
  text-align: center;
  padding: 2px 4px;
  font-weight: 600;
}}

/* Disc files */
.disc-files {{
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}}
.disc-file-link {{
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.65rem;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 500;
  transition: all 0.2s;
  text-decoration: none;
}}
.disc-file-link:hover {{
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
  text-decoration: none;
}}

/* Highlight search matches */
mark {{
  background: var(--highlight);
  color: #000;
  border-radius: 2px;
  padding: 0 1px;
}}

/* No results */
.no-results {{
  text-align: center;
  padding: 3rem 1rem;
  color: var(--text2);
}}
.no-results .emoji {{ font-size: 3rem; margin-bottom: 0.5rem; }}

/* Footer */
.footer {{
  text-align: center;
  padding: 2rem 1rem;
  color: var(--text2);
  font-size: 0.8rem;
  border-top: 1px solid var(--border);
  margin-top: 2rem;
}}

/* Scroll to top */
.scroll-top {{
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  display: none;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  z-index: 50;
}}
.scroll-top.visible {{ display: flex; }}

@media (max-width: 600px) {{
  .item-list {{
    grid-template-columns: 1fr;
  }}
  .stats {{ gap: 1rem; }}
  .search-inner {{ flex-direction: column; }}
  .filters {{ width: 100%; justify-content: center; }}
}}
</style>
</head>
<body>

<div class="header">
  <h1>💿 Twilight Warez CD Collection</h1>
  <div class="subtitle">Searchable index of games & software across all releases (1996–2000)</div>
  <div class="stats">
    <div class="stat"><div class="stat-num">{total_releases}</div><div class="stat-label">Releases</div></div>
    <div class="stat"><div class="stat-num">{total_games}</div><div class="stat-label">Games</div></div>
    <div class="stat"><div class="stat-num">{total_apps}</div><div class="stat-label">Apps</div></div>
    <div class="stat"><div class="stat-num">{total_games + total_apps}</div><div class="stat-label">Total Items</div></div>
  </div>
</div>

<div class="search-container">
  <div class="search-inner">
    <div class="search-box">
      <span class="icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search games, apps, or release number..." autofocus>
    </div>
    <div class="filters">
      <button class="filter-btn active" data-filter="all">All</button>
      <button class="filter-btn" data-filter="games">🎮 Games</button>
      <button class="filter-btn" data-filter="apps">💾 Apps</button>
    </div>
    <div class="result-count" id="resultCount"></div>
  </div>
</div>

<div class="content" id="content"></div>

<button class="scroll-top" id="scrollTop" title="Back to top">↑</button>

<div class="footer">
  <p>Data sourced from Twilight CD disc menus (LIST.TXT) and <a href="https://twilight-cd.com/releases/">twilight-cd.com</a></p>
  <p>Archive: <a href="https://archive.org/download/twilight-warez-cd-pack-1-tm-89/">archive.org/download/twilight-warez-cd-pack-1-tm-89</a></p>
</div>

<script>
const RELEASES = {js_data};

let currentFilter = 'all';
let searchTerm = '';
let openCards = new Set();

function escapeHtml(str) {{
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function highlightMatch(text, term) {{
  if (!term) return escapeHtml(text);
  const escaped = term.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
  const regex = new RegExp('(' + escaped + ')', 'gi');
  return escapeHtml(text).replace(regex, '<mark>$1</mark>');
}}

function getDiscLabel(rel) {{
  const discs = rel.discs || [];
  const letters = discs.map(d => d.letter).filter(Boolean);
  if (letters.length > 0) {{
    return letters.map(l => 'Disc ' + l.toUpperCase()).join(' + ');
  }}
  return 'Single disc';
}}

function itemMatches(item, term) {{
  return item.toLowerCase().includes(term.toLowerCase());
}}

function releaseMatches(rel, term, filter) {{
  if (!term && filter === 'all') return true;
  const t = term.toLowerCase();

  // Check release number
  if (t && (String(rel.release).includes(t) || ('twilight ' + rel.release).includes(t) || ('twilight' + rel.release).includes(t))) {{
    if (filter === 'all') return true;
    if (filter === 'games' && rel.games.length > 0) return true;
    if (filter === 'apps' && rel.apps.length > 0) return true;
  }}

  const showGames = filter === 'all' || filter === 'games';
  const showApps = filter === 'all' || filter === 'apps';

  if (showGames && rel.games.some(g => !t || itemMatches(g, t))) return true;
  if (showApps && rel.apps.some(a => !t || itemMatches(a, t))) return true;

  return false;
}}

function getMatchingItems(items, term) {{
  if (!term) return items;
  return items.filter(i => itemMatches(i, term));
}}

function render() {{
  const container = document.getElementById('content');
  let html = '';
  let visibleCount = 0;
  let matchCount = 0;

  for (const rel of RELEASES) {{
    const matches = releaseMatches(rel, searchTerm, currentFilter);
    if (!matches) continue;
    visibleCount++;

    const showGames = currentFilter === 'all' || currentFilter === 'games';
    const showApps = currentFilter === 'all' || currentFilter === 'apps';

    const matchedGames = showGames ? getMatchingItems(rel.games, searchTerm) : [];
    const matchedApps = showApps ? getMatchingItems(rel.apps, searchTerm) : [];

    // If searching, show all if release number matches, otherwise show only matching items
    const dispGames = searchTerm && !String(rel.release).includes(searchTerm.toLowerCase()) ? matchedGames : (showGames ? rel.games : []);
    const dispApps = searchTerm && !String(rel.release).includes(searchTerm.toLowerCase()) ? matchedApps : (showApps ? rel.apps : []);

    matchCount += matchedGames.length + matchedApps.length;

    const isOpen = openCards.has(rel.release) || !!searchTerm;

    html += '<div class="release-card' + (isOpen ? ' open' : '') + '" data-release="' + rel.release + '">';
    html += '<div class="release-header" onclick="toggleCard(' + rel.release + ')">';
    html += '<div class="release-num">#' + rel.release + '</div>';
    html += '<div class="release-title">';
    html += '<div class="name">Twilight ' + rel.release + '</div>';
    html += '<div class="disc-info">' + getDiscLabel(rel) + '</div>';
    html += '</div>';
    html += '<div class="release-badges">';
    if (rel.games.length) html += '<span class="badge badge-game">🎮 ' + rel.games.length + '</span>';
    if (rel.apps.length) html += '<span class="badge badge-app">💾 ' + rel.apps.length + '</span>';
    html += '</div>';
    html += '<span class="chevron">▶</span>';
    html += '</div>';

    html += '<div class="release-body">';

    // Cover images
    if (rel.covers && rel.covers.length > 0) {{
      html += '<div class="covers-row">';
      for (const c of rel.covers) {{
        const label = c.type === 'DVD' ? 'DVD Cover' : (c.type === 'CDa' ? 'CD A Cover' : 'CD B Cover');
        html += '<a class="cover-link" href="' + c.url + '" target="_blank" title="' + label + ' (click for full size)">';
        html += '<img src="' + c.thumb + '" alt="' + label + '" loading="lazy">';
        html += '<span class="cover-label">' + label + '</span>';
        html += '</a>';
      }}
      html += '</div>';
    }}

    // Disc file download links
    if (rel.files && rel.files.length > 0) {{
      html += '<div class="disc-files">';
      for (const f of rel.files) {{
        const ext = f.filename.split('.').pop().toUpperCase();
        html += '<a class="disc-file-link" href="' + f.url + '" title="Download ' + f.filename + '">💿 ' + f.filename + ' <span style="color:var(--text2);font-size:0.7rem">(' + ext + ')</span></a>';
      }}
      html += '</div>';
    }}

    if (dispGames.length > 0) {{
      html += '<div class="section-label games">🎮 Games (' + dispGames.length + ')</div>';
      html += '<div class="item-list">';
      for (const g of dispGames) {{
        html += '<div class="item"><span class="type-dot game"></span>' + highlightMatch(g, searchTerm) + '</div>';
      }}
      html += '</div>';
    }}
    if (dispApps.length > 0) {{
      html += '<div class="section-label apps">💾 Applications (' + dispApps.length + ')</div>';
      html += '<div class="item-list">';
      for (const a of dispApps) {{
        html += '<div class="item"><span class="type-dot app"></span>' + highlightMatch(a, searchTerm) + '</div>';
      }}
      html += '</div>';
    }}
    if (dispGames.length === 0 && dispApps.length === 0) {{
      html += '<div style="color:var(--text2);font-size:0.85rem;padding:0.5rem 0">No matching items in this release</div>';
    }}
    html += '</div></div>';
  }}

  if (visibleCount === 0) {{
    html = '<div class="no-results"><div class="emoji">🔍</div><p>No results found for "<strong>' + escapeHtml(searchTerm) + '</strong>"</p><p style="margin-top:0.5rem;font-size:0.85rem">Try a different search term or filter</p></div>';
  }}

  container.innerHTML = html;

  // Update count
  const countEl = document.getElementById('resultCount');
  if (searchTerm) {{
    countEl.textContent = matchCount + ' match' + (matchCount !== 1 ? 'es' : '') + ' in ' + visibleCount + ' release' + (visibleCount !== 1 ? 's' : '');
  }} else {{
    countEl.textContent = visibleCount + ' release' + (visibleCount !== 1 ? 's' : '');
  }}
}}

function toggleCard(num) {{
  if (openCards.has(num)) {{
    openCards.delete(num);
  }} else {{
    openCards.add(num);
  }}
  const card = document.querySelector('[data-release="' + num + '"]');
  if (card) card.classList.toggle('open');
}}

// Search
let debounceTimer;
document.getElementById('searchInput').addEventListener('input', (e) => {{
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {{
    searchTerm = e.target.value.trim();
    render();
  }}, 150);
}});

// Filters
document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    render();
  }});
}});

// Scroll to top
const scrollBtn = document.getElementById('scrollTop');
window.addEventListener('scroll', () => {{
  scrollBtn.classList.toggle('visible', window.scrollY > 400);
}});
scrollBtn.addEventListener('click', () => {{
  window.scrollTo({{ top: 0, behavior: 'smooth' }});
}});

// Keyboard shortcut: / to focus search
document.addEventListener('keydown', (e) => {{
  if (e.key === '/' && document.activeElement !== document.getElementById('searchInput')) {{
    e.preventDefault();
    document.getElementById('searchInput').focus();
  }}
  if (e.key === 'Escape') {{
    document.getElementById('searchInput').blur();
    document.getElementById('searchInput').value = '';
    searchTerm = '';
    render();
  }}
}});

// Initial render
render();
</script>
</body>
</html>'''

    return html


def main():
    print("Parsing data sources...")
    releases = build_index()
    print(f"  Found {len(releases)} releases")

    total_games = sum(len(r['games']) for r in releases.values())
    total_apps = sum(len(r['apps']) for r in releases.values())
    print(f"  Total games: {total_games}")
    print(f"  Total apps: {total_apps}")

    # Show coverage
    for num, data in releases.items():
        g = len(data['games'])
        a = len(data['apps'])
        discs = ', '.join(d['name'] for d in data['discs'])
        print(f"  Release {num:>2}: {g:>2} games, {a:>2} apps  [{discs}]")

    print("\nGenerating website...")
    html = generate_html(releases)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outpath = OUTPUT_DIR / "index.html"
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✓ Website generated: {outpath}")
    print(f"  File size: {os.path.getsize(outpath) / 1024:.1f} KB")
    print(f"\nOpen in browser: file://{outpath}")


if __name__ == '__main__':
    main()
