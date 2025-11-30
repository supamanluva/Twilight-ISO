#!/bin/bash
# Simple wrapper to run the downloader without manually activating venv

cd "$(dirname "$0")"
source venv/bin/activate
python download_twilight.py "$@"
