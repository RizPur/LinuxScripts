#!/bin/bash

set -e
set -o pipefail

source ~/.bashrc

# Load environment variables
if [ -f "$(dirname "$0")/.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/.env" | xargs)
fi

LOG_FILE="${LOG_FILE:-~/Scripts/logs.log}"
LAST_BACKUP_FILE="${LAST_BACKUP_FILE:-~/Scripts/last_backup_time.txt}"
SRC_DIR="${WORKFLOWS_SRC_DIR:-~/Documents/Eurecom/8-Semester/Workflows}"
DEST_DIR="${WORKFLOWS_DEST_DIR:-~/Google/Workflow}"

mkdir -p "$DEST_DIR"

# Get last backup timestamp
if [[ -f "$LAST_BACKUP_FILE" ]]; then
    LAST_BACKUP_TIME=$(cat "$LAST_BACKUP_FILE")
else
    LAST_BACKUP_TIME=0  # If no backup has been done, process all files
fi

# Ensure pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo "[$(date)] ❌ ERROR: Pandoc is not installed! Install it using 'sudo apt install pandoc'" | tee -a "$LOG_FILE"
    exit 1
fi

echo "[$(date)] 🔄 Starting workflow backup..." | tee -a "$LOG_FILE"

# Track if any files were processed
FILES_PROCESSED=0

# Convert only modified .md files
for file in "$SRC_DIR"/*.md; do
    if [[ -f "$file" ]]; then
        FILE_MOD_TIME=$(stat -c %Y "$file")

        # Check if file was modified after the last backup
        if [[ "$FILE_MOD_TIME" -gt "$LAST_BACKUP_TIME" ]]; then
            filename=$(basename "$file" .md)

            if pandoc "$file" --pdf-engine=xelatex -V mainfont="Noto Sans" -o "$DEST_DIR/$filename.pdf"; then
                echo "[$(date)] ✅ SUCCESS: Converted $file to $DEST_DIR/$filename.pdf" | tee -a "$LOG_FILE"
                FILES_PROCESSED=1
            else
                echo "[$(date)] ❌ ERROR: Failed to convert $file" | tee -a "$LOG_FILE"
            fi
        fi
    fi
done

# Update last backup timestamp only if files were processed
if [[ "$FILES_PROCESSED" -eq 1 ]]; then
    date +%s > "$LAST_BACKUP_FILE"
    echo "[$(date)] 📅 Updated last backup timestamp." | tee -a "$LOG_FILE"
else
    echo "[$(date)] 🔄 No new changes detected, skipping backup." | tee -a "$LOG_FILE"
fi

echo "[$(date)] 🎉 Backup process completed!" | tee -a "$LOG_FILE"

