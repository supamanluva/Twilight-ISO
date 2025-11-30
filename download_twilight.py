#!/usr/bin/env python3
"""
Twilight ISO Downloader
Downloads all files from the Archive.org Twilight Warez CD Pack collection
"""

import os
import sys
import requests
from urllib.parse import urljoin, unquote
from pathlib import Path
from tqdm import tqdm
import argparse
from bs4 import BeautifulSoup


class TwilightDownloader:
    def __init__(self, base_url, output_dir, file_types=None, skip_thumbs=False):
        self.base_url = base_url.rstrip('/')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.file_types = file_types or []
        self.skip_thumbs = skip_thumbs
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        
    def get_file_list(self):
        """Scrape the Archive.org page to get list of all files"""
        print(f"Fetching file list from {self.base_url}...")
        response = self.session.get(self.base_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        files = []
        
        # Find all links in the file listing
        for link in soup.find_all('a'):
            href = link.get('href')
            if not href or href.startswith('?') or href == '../':
                continue
                
            # Skip if it's a "View Contents" link
            if 'View Contents' in link.get_text():
                continue
                
            filename = unquote(href)
            
            # Skip thumbnails if requested
            if self.skip_thumbs and '_thumb.' in filename:
                continue
            
            # Filter by file types if specified
            if self.file_types:
                ext = os.path.splitext(filename)[1].lower().lstrip('.')
                if ext not in self.file_types:
                    continue
            
            file_url = urljoin(self.base_url + '/', href)
            files.append((filename, file_url))
        
        print(f"Found {len(files)} files to download")
        return files
    
    def download_file(self, filename, url, resume=True):
        """Download a single file with progress bar and resume capability"""
        filepath = self.output_dir / filename
        
        # Check if file already exists
        if filepath.exists():
            existing_size = filepath.stat().st_size
        else:
            existing_size = 0
        
        headers = {}
        if resume and existing_size > 0:
            headers['Range'] = f'bytes={existing_size}-'
            mode = 'ab'
        else:
            mode = 'wb'
            existing_size = 0
        
        try:
            response = self.session.get(url, headers=headers, stream=True, timeout=30)
            
            # If server doesn't support resume, start from beginning
            if response.status_code == 416:  # Range not satisfiable
                print(f"  Resume not supported for {filename}, starting fresh")
                response = self.session.get(url, stream=True, timeout=30)
                mode = 'wb'
                existing_size = 0
            elif response.status_code == 206:  # Partial content
                print(f"  Resuming download of {filename} from byte {existing_size}")
            
            response.raise_for_status()
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            if response.status_code == 206:
                total_size += existing_size
            
            # Check if already fully downloaded
            if existing_size > 0 and existing_size >= total_size:
                print(f"✓ {filename} already downloaded")
                return True
            
            # Download with progress bar
            with open(filepath, mode) as f:
                with tqdm(
                    total=total_size,
                    initial=existing_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=filename[:50]
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            print(f"✓ {filename} downloaded successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Error downloading {filename}: {e}")
            return False
        except KeyboardInterrupt:
            print(f"\n⚠ Download interrupted for {filename}")
            raise
        except Exception as e:
            print(f"✗ Unexpected error downloading {filename}: {e}")
            return False
    
    def download_all(self):
        """Download all files from the collection"""
        files = self.get_file_list()
        
        if not files:
            print("No files found to download!")
            return
        
        print(f"\nStarting download to: {self.output_dir.absolute()}\n")
        
        successful = 0
        failed = 0
        
        for i, (filename, url) in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Downloading: {filename}")
            try:
                if self.download_file(filename, url):
                    successful += 1
                else:
                    failed += 1
            except KeyboardInterrupt:
                print("\n\n⚠ Download interrupted by user")
                print(f"Downloaded: {successful}, Failed: {failed}, Remaining: {len(files) - i}")
                sys.exit(1)
        
        print(f"\n{'='*60}")
        print(f"Download complete!")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {len(files)}")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Download all files from Archive.org Twilight Warez CD Pack collection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download everything
  python download_twilight.py
  
  # Download only ISO files
  python download_twilight.py --types iso
  
  # Download only cover images (excluding thumbnails)
  python download_twilight.py --types jpg --skip-thumbs
  
  # Download to a specific directory
  python download_twilight.py --output /path/to/downloads
  
  # Download ISOs and BIN files only
  python download_twilight.py --types iso bin
        """
    )
    
    parser.add_argument(
        '--url',
        default='https://archive.org/download/twilight-warez-cd-pack-1-tm-89/',
        help='Archive.org collection URL (default: Twilight Warez CD Pack)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='./downloads',
        help='Output directory for downloaded files (default: ./downloads)'
    )
    
    parser.add_argument(
        '--types', '-t',
        nargs='+',
        help='Only download specific file types (e.g., iso bin jpg)'
    )
    
    parser.add_argument(
        '--skip-thumbs',
        action='store_true',
        help='Skip thumbnail images (_thumb.jpg files)'
    )
    
    args = parser.parse_args()
    
    # Normalize file types to lowercase
    if args.types:
        args.types = [t.lower().lstrip('.') for t in args.types]
    
    print("="*60)
    print("Twilight ISO Downloader")
    print("="*60)
    print(f"Source: {args.url}")
    print(f"Output: {args.output}")
    if args.types:
        print(f"File types: {', '.join(args.types)}")
    if args.skip_thumbs:
        print("Skipping thumbnail images")
    print("="*60)
    
    try:
        downloader = TwilightDownloader(
            base_url=args.url,
            output_dir=args.output,
            file_types=args.types,
            skip_thumbs=args.skip_thumbs
        )
        downloader.download_all()
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
