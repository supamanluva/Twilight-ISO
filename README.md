# Twilight ISO Downloader

A Python tool to download all files from the Archive.org Twilight Warez CD Pack collection.

## Features

- 📥 Downloads all files from the collection
- 📊 Progress bars for each download
- ⏸️ Resume capability for interrupted downloads
- 🎯 Filter by file type (ISO, BIN, JPG, etc.)
- 🚫 Option to skip thumbnail images
- 🔄 Automatic retry and error handling

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Download everything:

```bash
python download_twilight.py
```

### Advanced Options

Download only ISO files:

```bash
python download_twilight.py --types iso
```

Download only ISO and BIN files:

```bash
python download_twilight.py --types iso bin
```

Download cover images (excluding thumbnails):

```bash
python download_twilight.py --types jpg --skip-thumbs
```

Download to a specific directory:

```bash
python download_twilight.py --output /path/to/downloads
```

### All Options

```
--url              Archive.org collection URL (default: Twilight Warez CD Pack)
--output, -o       Output directory (default: ./downloads)
--types, -t        Only download specific file types (e.g., iso bin jpg)
--skip-thumbs      Skip thumbnail images (_thumb.jpg files)
```

## File Types Available

The collection includes:
- **ISO files** - Disc image files (ranging from ~640MB to 7.9GB each)
- **BIN files** - Binary disc images
- **JPG files** - Cover art images
- **XML files** - Metadata files
- **Torrent files** - BitTorrent metadata

## Resume Downloads

If a download is interrupted, simply run the command again. The script will automatically resume from where it left off.

## Storage Requirements

⚠️ **Warning**: The complete collection is very large (hundreds of GB). Make sure you have sufficient disk space before downloading everything.

To check approximate sizes:
- Small ISOs (001-047): ~600-800MB each
- Large ISOs (048-089): ~4-8GB each
- Cover images: ~100KB-2MB each
- Total collection: ~500GB+

## Examples

Download only the first 10 ISOs (001-010):
```bash
python download_twilight.py --types iso
# Then manually ctrl+c after 10 files
```

Get all covers but no thumbnails:
```bash
python download_twilight.py --types jpg --skip-thumbs
```

Download everything to an external drive:
```bash
python download_twilight.py --output /mnt/external/twilight-collection
```

## License

This tool is for personal use. All content belongs to Archive.org and the original uploaders.

## Source

Collection URL: https://archive.org/download/twilight-warez-cd-pack-1-tm-89/
