#!/bin/bash

# This script lists all files in the current repository that are not ignored by git,
# and prints their contents.
# For files in the 'fixtures' directory, it prints '[contents skipped]' instead of the content.
#
# Usage: list_all_files.sh [--with-results]
#   --with-results  Include results/ directory contents

WITH_RESULTS=false
if [ "$1" = "--with-results" ]; then
    WITH_RESULTS=true
fi

# Check if git is installed
if ! command -v git &> /dev/null
then
    echo "git could not be found. Please install git to run this script."
    exit 1
fi

# Check if inside a git repository
if ! git rev-parse --is-inside-work-tree &> /dev/null
then
    echo "Not inside a git repository."
    exit 1
fi

SEPARATOR="========================================"

print_file() {
    local file_path="$1"

    if [ ! -f "$file_path" ]; then
        return
    fi

    echo "" # for spacing
    echo "$SEPARATOR"
    echo "FILE: $file_path"
    echo "$SEPARATOR"

    # Skip certain directories unless --with-results is set for results/
    local should_skip=false
    if [[ ("$file_path" == *fixtures/* && "$file_path" != *simple/*) || "$file_path" == *scripts/* || "$file_path" == *docs/* ]]; then
        should_skip=true
    elif [[ "$file_path" == results/* && "$WITH_RESULTS" = false ]]; then
        should_skip=true
    fi

    if [ "$should_skip" = true ]; then
        echo "[contents skipped]"
    elif file -b --mime-encoding "$file_path" | grep -q "binary"; then
        echo "[Binary file - contents not shown]"
    else
        if [ -s "$file_path" ]; then
            cat "$file_path"
            if [ "$(tail -c1 "$file_path")" != "" ]; then
                echo
            fi
        else
            echo "[Empty file]"
        fi
    fi
    echo "$SEPARATOR"
}

# Print README.md first if it exists
if [ -f "README.md" ]; then
    print_file "README.md"
fi

# Get all tracked and untracked files, excluding standard gitignores.
# The files are piped to a while loop to handle file paths with spaces correctly.
git ls-files --cached --others --exclude-standard | sort | while IFS= read -r file_path; do
    # Skip README.md since we already printed it
    if [ "$file_path" = "README.md" ]; then
        continue
    fi
    print_file "$file_path"
done
