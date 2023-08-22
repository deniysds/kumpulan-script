#!/bin/bash

# Specify the directory path
directory="/path/to/directory"

# Use a loop to iterate over the files in the directory
for file in "$directory"/*; do
    # Check if the item is a file (not a directory)
    if [[ -f "$file" ]]; then
        # Extract and print the file name
        filename=$(basename "$file")
        tar -cjvf "$filename.tar.bz2" "$filename"
    fi
done