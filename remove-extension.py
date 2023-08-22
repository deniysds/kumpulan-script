import os

def remove_file_extension(filename):
    # Split the filename and its extension
    name, extension = os.path.splitext(filename)
    return name

# Example usage
filename_with_extension = "example_file.txt"
filename_without_extension = remove_file_extension(filename_with_extension)
print(filename_without_extension)  # Output: "example_file"