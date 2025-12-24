from pathlib import Path
from .exceptions import InvalidInputFileError

# =========================================================================== #

"""
Validate that the memories_history.html file exists and is valid

Args:
    file_path: Path to memories_history.html

Returns:
    Path object if valid

Raises:
    InvalidInputFileError: If file doesn't exist or is invalid
"""


def validate_input_file(file_path: str) -> Path:

    path = Path(file_path)

    # Check that file is present in directory
    if not path.exists():
        raise InvalidInputFileError(
            f"File not found: {file_path}\n"
            f"Please provide the memories_history.html file from Snapchat."
        )

    # Check that file is not a directory or empty
    if not path.is_file():
        raise InvalidInputFileError(f"{file_path} is not a file.")
    if path.stat().st_size == 0:
        raise InvalidInputFileError(f"{file_path} is empty.")

    return path

# =========================================================================== #
