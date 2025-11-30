#!/usr/bin/env python3
"""
Example usage of the Twilight Downloader
This demonstrates how to test the downloader with just a few files
"""

from download_twilight import TwilightDownloader

# Test with just downloading metadata files (small files)
print("Testing downloader with small files (metadata only)...")
print()

downloader = TwilightDownloader(
    base_url='https://archive.org/download/twilight-warez-cd-pack-1-tm-89/',
    output_dir='./test_downloads',
    file_types=['xml', 'torrent'],  # Only small metadata files for testing
    skip_thumbs=True
)

try:
    downloader.download_all()
except KeyboardInterrupt:
    print("\nTest interrupted")
