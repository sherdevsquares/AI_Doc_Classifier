import puremagic
## library used to find the mime type.

    # Example: get the MIME type of a file
file_path = r"xxxxxxx" # Replace with an actual local file path
try:
    mimetype = puremagic.from_file(file_path, mime=True)
    print(f"MIME type of {file_path}: {mimetype}")
except Exception as e:
    print(f"Error using libmagic: {e}")
