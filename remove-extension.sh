#!/bin/bash

# Example file name
file_name="example_file.txt"

# Remove the file extension
file_name_without_extension="${file_name%.*}"

# Print the result
echo "File name without extension: $file_name_without_extension"