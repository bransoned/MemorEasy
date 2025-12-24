from .exceptions import *
from pathlib import Path
import shutil
import sys

# =========================================================================== #

"""
Find dependency executable

Returns:
    Path to dependency

Raises:
    DependencyError: If dependency cannot be found
"""
def find_dependency(dependency_str: str) -> str:

    exe_name = f"{dependency_str}.exe" if sys.platform.startswith("win") else f"{dependency_str}"

    # If bundle
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        bundled = base / "bin" / exe_name
        if bundled.exists():
            return str(bundled)

    # Try system PATH
    system_path = shutil.which(exe_name)
    if system_path:
        return system_path

    raise DependencyError(
        f"{depency_str} not found. Please install {dependency_str} or use the provided bundled executable."
        "For further installation instructions, reference the README."
    )

# =========================================================================== #

