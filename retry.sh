#!/bin/bash
# Retry failed downloads

cd "$(dirname "$0")"
source venv/bin/activate
python retry_failed.py "$@"
