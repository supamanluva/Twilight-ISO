# Twilight ISO Collection

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/badge/github-supamanluva%2FTwilight--ISO-black)](https://github.com/supamanluva/Twilight-ISO)
[![Website](https://img.shields.io/badge/Browse-Online-green)](https://supamanluva.github.io/Twilight-ISO/)

Download, verify, search, and browse the complete [Archive.org Twilight Warez CD Pack](https://archive.org/details/twilight-warez-cd-pack-1-tm-89) collection (releases 1–89, 117 disc images).

**🌐 [Browse the collection online](https://supamanluva.github.io/Twilight-ISO/)**

## Features

- 📥 **Download** all files from archive.org with resume support
- ✅ **Verify** downloads against metadata (size + MD5 checksums)
- 🔧 **Auto-fix** corrupt or incomplete downloads
- 🌐 **Searchable website** — 89 releases, 2,749 games, 2,452 apps, with cover art and download links
- 🖼️ **Cover art** — 132 cover images linked to every release
- 💿 **Disc file links** — direct archive.org download links for all 125 ISO/BIN files
- 🔍 **CLI search** — find which disc has a specific game
- 💾 **USB prep** — format and load ISOs onto a USB drive for retro use

## Quick Start

```bash
git clone https://github.com/supamanluva/Twilight-ISO.git
cd Twilight-ISO
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
./start.sh
```

---

## Downloader

### Download

```bash
# Interactive menu
./start.sh

# Download everything
python download_twilight.py

# Download only ISOs
python download_twilight.py --types iso

# Download to a specific directory
python download_twilight.py --types iso --output /mnt/external/twilight
```

### Verify Downloads

Compares files on disk against the archive.org `_files.xml` metadata (auto-downloaded on first run).

```bash
# Quick size check (instant)
python download_twilight.py --verify --types iso

# Thorough check with MD5 checksums (reads every byte)
python download_twilight.py --verify-md5 --types iso
```

### Fix Corrupt Downloads

Detects bad files and re-downloads them automatically:

```bash
python download_twilight.py --fix --types iso
```

### All Downloader Options

| Flag | Description |
|------|-------------|
| `--url URL` | Archive.org collection URL |
| `--output, -o DIR` | Output directory (default: `./downloads`) |
| `--types, -t ext [...]` | Filter by file type (e.g. `iso bin jpg`) |
| `--skip-thumbs` | Skip thumbnail images |
| `--verify` | Check downloads (size) |
| `--verify-md5` | Check downloads (size + MD5) |
| `--fix` | Re-download any corrupt/incomplete files |

---

## Searchable Website

A static single-page website that indexes every game and app across all releases. Browse 89 releases with cover art, disc download links, and instant search.

| Stat | Count |
|------|-------|
| Releases | 89 |
| Games | 1,626 |
| Apps | 2,073 |
| Cover images | 132 (across 78 releases) |
| Disc files | 125 ISO/BIN download links |

### Build the Website

```bash
python3 tools/build_website.py
```

This reads the extracted disc data from `downloads/list_txt_files/` and `downloads/twilight_games_list.txt`, scans for cover images and ISO/BIN files, and generates `docs/index.html`.

### View the Website

Open `docs/index.html` in any browser, or serve locally:

```bash
cd docs && python3 -m http.server 8765
# Open http://localhost:8765
```

Or host on GitHub Pages (enable Pages on the `docs/` folder in repo settings).

### Website Features

- 🔎 Instant search across all games and apps
- 🎮 Filter by Games or Apps
- 📀 Browse all 89 releases (1–89)
- 🖼️ Cover art thumbnails — click for full-size images on archive.org
- 💿 Direct download links for every ISO/BIN file
- ⌨️ Keyboard shortcuts: `/` to search, `Esc` to clear
- 📱 Mobile responsive, dark theme
- Releases without game/app data still show covers and download links

---

## CLI Game Search

Search for games/apps from the terminal:

```bash
./tools/search_games.sh quake
./tools/search_games.sh "need for speed"
```

Output shows which disc(s) contain the matching title.

---

## USB Prep Tool

Format a USB drive and copy ISOs onto it for use on retro machines:

```bash
sudo ./tools/prep_win98_usb.sh
```

Features:
- Auto-detects USB drives (excludes system disks)
- NVMe-safe parent disk detection
- Checks available capacity before copying
- Shows progress with rsync
- Cleanup on exit via trap

---

## Project Structure

```
Twilight-ISO/
├── download_twilight.py    # Main downloader (download/verify/fix)
├── retry_failed.py         # Auto-detect and retry bad downloads
├── start.sh                # Interactive menu
├── download.sh             # Quick download wrapper
├── retry.sh                # Quick retry wrapper
├── QUICKSTART.sh           # Usage reference
├── requirements.txt        # Python dependencies
├── tools/
│   ├── build_website.py    # Generate searchable website from disc data
│   ├── search_games.sh     # CLI game search
│   └── prep_win98_usb.sh   # USB drive prep for retro use
├── docs/
│   └── index.html          # Generated website (GitHub Pages ready)
├── downloads/              # Downloaded ISOs and data (gitignored)
│   ├── *.iso
│   ├── list_txt_files/     # Extracted disc content listings
│   └── twilight_games_list.txt
└── .gitignore
```

## Storage Requirements

| Releases | Size each | Notes |
|----------|-----------|-------|
| 001–014 | 640–700 MB | CD-sized, single disc |
| 015–047 | 640–700 MB × 2 | CD-sized, dual disc (a/b) |
| 048–060 | 1.2–4.6 GB | Transitional (mixed CD/DVD) |
| 061–079 | 4–4.6 GB | DVD-sized |
| 080–086 | 7.8–8.4 GB | Dual-layer DVD |
| 087–089 | 7.8–8.4 GB × 2 | Dual-layer, dual disc (A/B) |
| **Total** | **~500+ GB** | **117 disc images, 265 JPGs** |

## Data Sources

The website content is built from multiple data sources:

1. **LIST.TXT files** — extracted from disc menus inside the ISOs (best data, has both games & apps)
2. **twilight_games_list.txt** — scraped game listings (games only, used as fallback)
3. **Folder name extraction** — for discs without LIST.TXT, folder names from Apps/ and Games/ directories are used (via mount or 7z for UDF-format discs)
4. **Cover images** — `TWILIGHT {NNN} CDa/CDb/DVD Cover.jpg` files from archive.org (132 full-size + 132 thumbnails)
5. **Disc files** — ISO/BIN files mapped to releases by filename pattern

## License

MIT — see [LICENSE](LICENSE).

## Source

Collection: <https://archive.org/details/twilight-warez-cd-pack-1-tm-89>
