#!/usr/bin/env python3
"""
Twilight ISO Downloader
Downloads all files from the Archive.org Twilight Warez CD Pack collection
"""

import os
import sys
import hashlib
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, unquote
from pathlib import Path
from tqdm import tqdm
import argparse
from bs4 import BeautifulSoup


# Archive.org identifier for this collection
ARCHIVE_ID = 'twilight-warez-cd-pack-1-tm-89'
METADATA_XML = f'{ARCHIVE_ID}_files.xml'


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
        self._metadata = None  # lazy-loaded from XML
        
    # ------------------------------------------------------------------
    #  Metadata / integrity helpers
    # ------------------------------------------------------------------

    def _load_metadata(self):
        """Load expected sizes and MD5s from the archive.org _files.xml.

        Downloads the XML first if it isn't already on disk.
        Returns dict: filename -> {'size': int, 'md5': str}
        """
        if self._metadata is not None:
            return self._metadata

        xml_path = self.output_dir / METADATA_XML
        if not xml_path.exists():
            print(f"Downloading metadata: {METADATA_XML} …")
            url = f"{self.base_url}/{METADATA_XML}"
            r = self.session.get(url, timeout=60)
            r.raise_for_status()
            xml_path.write_bytes(r.content)

        tree = ET.parse(xml_path)
        meta = {}
        for f in tree.getroot().findall('file'):
            name = f.get('name', '')
            size_txt = f.findtext('size')
            md5_txt = f.findtext('md5')
            if size_txt:
                meta[name] = {
                    'size': int(size_txt),
                    'md5': md5_txt or '',
                }
        self._metadata = meta
        return meta

    @staticmethod
    def _md5_file(path, chunk_size=1 << 20):
        """Compute MD5 hex digest for a file on disk."""
        h = hashlib.md5()
        with open(path, 'rb') as f:
            while True:
                buf = f.read(chunk_size)
                if not buf:
                    break
                h.update(buf)
        return h.hexdigest()

    def verify_file(self, filename, check_md5=False):
        """Check a single downloaded file against metadata.

        Returns (status, detail) where status is one of:
          'ok'       – size (and optionally md5) match
          'size'     – size mismatch
          'md5'      – size ok but md5 mismatch
          'missing'  – file does not exist on disk
          'unknown'  – no metadata available for this file
        """
        meta = self._load_metadata()
        if filename not in meta:
            return ('unknown', 'no metadata entry')

        expected = meta[filename]
        filepath = self.output_dir / filename

        if not filepath.exists():
            return ('missing', f'expected {expected["size"]:,} bytes')

        actual_size = filepath.stat().st_size
        if actual_size != expected['size']:
            pct = actual_size / expected['size'] * 100 if expected['size'] else 0
            return ('size', f'expected {expected["size"]:,}  got {actual_size:,} ({pct:.1f}%)')

        if check_md5 and expected['md5']:
            actual_md5 = self._md5_file(filepath)
            if actual_md5 != expected['md5']:
                return ('md5', f'expected {expected["md5"]}  got {actual_md5}')

        return ('ok', '')

    def verify_all(self, file_types=None, check_md5=False):
        """Verify every file (or only certain extensions) against metadata.

        Returns lists: (ok, bad)  where bad items are (filename, status, detail).
        """
        meta = self._load_metadata()
        ok, bad = [], []

        for filename, info in sorted(meta.items()):
            if file_types:
                ext = os.path.splitext(filename)[1].lower().lstrip('.')
                if ext not in file_types:
                    continue
            status, detail = self.verify_file(filename, check_md5=check_md5)
            if status == 'ok':
                ok.append(filename)
            elif status == 'unknown':
                continue
            else:
                bad.append((filename, status, detail))
        return ok, bad

    # ------------------------------------------------------------------
    #  File listing
    # ------------------------------------------------------------------

    def get_file_list(self):
        """Scrape the Archive.org page to get list of all files"""
        print(f"Fetching file list from {self.base_url}...")
        response = self.session.get(self.base_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        files = []
        
        # Find all links in the file listing table
        for link in soup.find_all('a'):
            href = link.get('href')
            if not href:
                continue
            
            # Skip navigation links, external links, and other non-file links
            if (href.startswith('http') or 
                href.startswith('?') or 
                href.startswith('#') or
                href.startswith('/') or
                href == '../' or
                href == '..'):
                continue
                
            # Skip if it's a "View Contents" link
            if 'View Contents' in link.get_text():
                continue
            
            # Only include files with extensions (actual downloadable files)
            if '.' not in href:
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

        # ---- post-download integrity check ----
        print("\nVerifying downloaded files …")
        ok_files, bad_files = self.verify_all(
            file_types=self.file_types or None
        )
        if bad_files:
            print(f"\n⚠  {len(bad_files)} file(s) failed verification:")
            for name, status, detail in bad_files:
                print(f"  [{status}] {name}: {detail}")
            print("\nRun with --verify to see full report,")
            print("or --fix to re-download corrupt/incomplete files.")
        else:
            print(f"✓ All {len(ok_files)} downloaded files verified OK")

    def fix(self, file_types=None, check_md5=False):
        """Verify all files and re-download any that are corrupt or missing."""
        print("Verifying existing files …")
        ok_files, bad_files = self.verify_all(
            file_types=file_types, check_md5=check_md5
        )
        print(f"  {len(ok_files)} OK, {len(bad_files)} need re-download")

        if not bad_files:
            print("\n✓ Everything looks good – nothing to fix!")
            return

        print(f"\nRe-downloading {len(bad_files)} file(s):\n")
        successful = 0
        failed = 0

        for i, (filename, status, detail) in enumerate(bad_files, 1):
            print(f"\n[{i}/{len(bad_files)}] ({status}) {filename}: {detail}")
            url = f"{self.base_url}/{filename}"
            filepath = self.output_dir / filename

            # Delete the partial/corrupt file so we get a clean download
            if filepath.exists():
                filepath.unlink()

            try:
                if self.download_file(filename, url, resume=False):
                    # Double-check after download
                    st, dt = self.verify_file(filename, check_md5=check_md5)
                    if st == 'ok':
                        successful += 1
                    else:
                        print(f"  ⚠ Still bad after re-download: {dt}")
                        failed += 1
                else:
                    failed += 1
            except KeyboardInterrupt:
                print(f"\n\n⚠ Fix interrupted. {successful} fixed, {failed} failed, "
                      f"{len(bad_files) - i} remaining")
                sys.exit(1)

        print(f"\n{'='*60}")
        print(f"Fix complete!")
        print(f"  Re-downloaded OK : {successful}")
        print(f"  Still failing    : {failed}")
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

    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify existing downloads against archive.org metadata (size check)'
    )

    parser.add_argument(
        '--verify-md5',
        action='store_true',
        help='Like --verify but also checks MD5 checksums (slower)'
    )

    parser.add_argument(
        '--fix',
        action='store_true',
        help='Verify and automatically re-download any corrupt/incomplete files'
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
    if args.verify or args.verify_md5:
        print("Mode: VERIFY")
    elif args.fix:
        print("Mode: FIX (verify + re-download bad files)")
    print("="*60)
    
    try:
        downloader = TwilightDownloader(
            base_url=args.url,
            output_dir=args.output,
            file_types=args.types,
            skip_thumbs=args.skip_thumbs
        )

        # --- verify / fix modes ---
        if args.verify or args.verify_md5:
            check_md5 = args.verify_md5
            ok, bad = downloader.verify_all(
                file_types=args.types, check_md5=check_md5
            )
            print(f"\n✓ {len(ok)} file(s) OK")
            if bad:
                print(f"✗ {len(bad)} file(s) FAILED:")
                for name, status, detail in bad:
                    print(f"  [{status:>7s}] {name}: {detail}")
                print(f"\nRun with --fix to re-download these automatically.")
                sys.exit(1)
            else:
                print("All files verified successfully!")
            sys.exit(0)

        if args.fix:
            downloader.fix(
                file_types=args.types, check_md5=args.verify_md5
            )
            sys.exit(0)

        # --- normal download ---
        downloader.download_all()

    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
