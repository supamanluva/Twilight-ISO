#!/bin/bash
# Quick start script for Twilight ISO Downloader

# Activate virtual environment
source venv/bin/activate

echo "Twilight ISO Downloader - Quick Start"
echo "====================================="
echo ""
echo "This will download ALL files from the Twilight Warez CD Pack collection"
echo "Warning: This is a very large collection (500+ GB)"
echo ""
echo "Options:"
echo "1. Download everything (full collection)"
echo "2. Download only ISO files"
echo "3. Download only cover images (no thumbnails)"
echo "4. Verify downloads (check for corrupt/incomplete files)"
echo "5. Fix downloads (re-download corrupt/incomplete files)"
echo "6. Custom options"
echo "7. Exit"
echo ""
read -p "Select an option (1-7): " choice

case $choice in
    1)
        echo "Starting full download..."
        python download_twilight.py
        ;;
    2)
        echo "Starting ISO download..."
        python download_twilight.py --types iso
        ;;
    3)
        echo "Starting cover image download..."
        python download_twilight.py --types jpg --skip-thumbs
        ;;
    4)
        echo "Verifying downloaded files..."
        python download_twilight.py --verify --types iso
        ;;
    5)
        echo "Fixing corrupt/incomplete downloads..."
        python download_twilight.py --fix --types iso
        ;;
    6)
        echo "Enter custom options (e.g., --types iso bin --output /path):"
        read -p "> " custom_opts
        python download_twilight.py $custom_opts
        ;;
    7)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
