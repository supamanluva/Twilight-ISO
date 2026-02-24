# Twilight ISO Collection

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/badge/github-supamanluva%2FTwilight--ISO-black)](https://github.com/supamanluva/Twilight-ISO)

Download, verify, search, and browse the complete [Archive.org Twilight Warez CD Pack](https://archive.org/details/twilight-warez-cd-pack-1-tm-89) collection (releases 1–89, 117 disc images).

## Features

- 📥 **Download** all files from archive.org with resume support
- ✅ **Verify** downloads against metadata (size + MD5 checksums)
- 🔧 **Auto-fix** corrupt or incomplete downloads
- 🌐 **Searchable website** — browse games & apps by release, search instantly
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

A static single-page website that indexes every game and app across all 117 discs. Features instant search, filter by games/apps, and shows which ISO each title is on.

### Build the Website

```bash
python3 tools/build_website.py
```

This reads the extracted disc data from `downloads/list_txt_files/` and generates `docs/index.html`.

### View the Website

Open `docs/index.html` in any browser, or host it on GitHub Pages.

**Live site:** *(enable GitHub Pages on the `docs/` folder in repo settings)*

### Website Features

- 🔎 Instant search across all games and apps
- 🎮 Filter by Games or Apps
- 📀 Browse by release number
- ⌨️ Keyboard shortcuts: `/` to search, `Esc` to clear
- 📱 Mobile responsive, dark theme

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
| 001–047 | 640–700 MB | CD-sized |
| 048–079 | 4–4.6 GB | DVD-sized |
| 080–089 | 7.8–8.4 GB | Dual-layer |
| **Total** | **~500+ GB** | |

## License

MIT — see [LICENSE](LICENSE).

## Source

Collection: <https://archive.org/details/twilight-warez-cd-pack-1-tm-89>
