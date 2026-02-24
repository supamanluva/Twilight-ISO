#!/usr/bin/env python3
"""
Retry / fix failed downloads.

Automatically detects corrupt or incomplete files by comparing them against
the archive.org _files.xml metadata, then re-downloads only the bad ones.

Usage:
  python retry_failed.py              # check sizes, re-download bad ISOs
  python retry_failed.py --all        # check ALL file types, not just ISOs
  python retry_failed.py --md5        # also verify MD5 checksums (slow)
"""

import sys
import os
import argparse

# Add the current directory to path to import the downloader
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from download_twilight import TwilightDownloader


def main():
    parser = argparse.ArgumentParser(description='Verify and re-download corrupt files')
    parser.add_argument('--all', action='store_true',
                        help='Check all file types (default: ISOs only)')
    parser.add_argument('--md5', action='store_true',
                        help='Also verify MD5 checksums (slower but thorough)')
    parser.add_argument('--types', nargs='+', default=None,
                        help='File types to check (e.g. iso bin)')
    args = parser.parse_args()

    base_url = "https://archive.org/download/twilight-warez-cd-pack-1-tm-89/"
    output_dir = "./downloads"

    file_types = args.types
    if not args.all and file_types is None:
        file_types = ['iso']

    print("=" * 70)
    print("TWILIGHT DOWNLOAD INTEGRITY CHECK & FIX")
    print("=" * 70)

    downloader = TwilightDownloader(
        base_url=base_url,
        output_dir=output_dir,
    )

    downloader.fix(file_types=file_types, check_md5=args.md5)


if __name__ == '__main__':
    main()
