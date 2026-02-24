#!/bin/bash

# Twilight Games Search Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAMES_LIST="${SCRIPT_DIR}/../downloads/twilight_games_list.txt"

if [ ! -f "$GAMES_LIST" ]; then
    echo "Error: twilight_games_list.txt not found!"
    echo "Run prep_win98_usb.sh first to generate the games list."
    exit 1
fi

if [ $# -eq 0 ]; then
    echo "Usage: $0 <search term>"
    echo "Example: $0 quake"
    echo "         $0 \"need for speed\""
    exit 1
fi

SEARCH_TERM="$*"

echo "Searching for: $SEARCH_TERM"
echo "========================================"

# Use awk to properly associate games with ISOs
results=$(awk -v search="$SEARCH_TERM" 'BEGIN{IGNORECASE=1} 
/^Twilight[0-9]+/ {iso=$0; next} 
/^====/ {next}
tolower($0) ~ tolower(search) && iso != "" && $0 !~ /^$/ {print "[" iso "] " $0}
' "$GAMES_LIST" | sort -u)

if [ -z "$results" ]; then
    echo "No matches found for: $SEARCH_TERM"
else
    echo "$results"
fi
