#!/bin/bash

# Replace "your_file.txt" with the actual file path
file_path="kumpulan-sra.txt"

# Check if the file exists
if [ -e "$file_path" ]; then
    # Open the file and read line by line
    while IFS= read -r line; do
        prefetch "$line" --max-size u
    done < "$file_path"
else
    echo "File not found: $file_path"
fi