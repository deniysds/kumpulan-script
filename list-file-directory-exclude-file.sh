#!/bin/bash

# Specify the directory path
directory="/path/to/directory"

# Specify the file to exclude
exclude_file="file_to_exclude.txt"

# Iterate over the files in the directory
for file in "$directory"/*; do
    # Check if the item is a file (not a directory)
    if [[ -f "$file" ]]; then
        # Extract and check the file name
        filename=$(basename "$file")
        
        # Skip the excluded file
        if [[ "$filename" == "$exclude_file" ]]; then
            continue
        fi

        # Print the file name
        echo "$filename"
    fi
done