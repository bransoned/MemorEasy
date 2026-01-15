from datetime import datetime, timezone
from .dependencies import find_dependency
from .exceptions import DependencyError, MemorEasyError
from pathlib import Path
import subprocess
import os

# =========================================================================== #

"""
Change the "modified date" in EXIF section to "created date" value

Args:
    path: File path of the file/directory to be edited
    date_time_str: Date to be written to file in format
      "YYYY-MM-DD HH:MM:SS" in UTC

Raises:
    FileNotFoundError: If path doesn't exist
    ValueError: If date_time_str format is invalid
    OSError: If timestamp cannot be set (permissions, etc)
"""


def set_file_timestamp(path, date_time_str) -> None:

    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    # Validate and parse date string
    try:
        dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
    except ValueError as e:
        raise ValueError(
            f"Invalid date format '{date_time_str}'."
            f"Expected 'YYYY-MM-DD HH:MM:SS'. Error: {e}"
        )

    # Convert to timestamp
    try:
        ts = dt.timestamp()
    except (ValueError, OSError) as e:
        raise ValueError(f"Cannot convert date to timestamp: {e}")

    # Set access and modified times
    try:
        os.utime(path, (ts, ts))
    except OSError as e:
        raise OSError(
            f"Failed to set timestamp on {path}: {e}."
            f"This may be due to file permissions or filesystem limitations."
        )

# =========================================================================== #


"""
Write EXIF metadata to image or video file

Args:
    file_path: Path to media file
    date_time_str: DateTime in format "YYYY-MM-DD HH:MM:SS" in UTC
    lat: Latitude decimal as a string
    lon: Longitude decimal as a string

Raises:
    FileNotFoundError: If file or directory doesn't exist
    DependencyError: If exiftool not found
    ValueError: If coordinates are invalid
    MemorEasyError: If exiftool fails
"""


def write_exif(
        file_path: Path,
        date_time_str: str,
        lat: str, lon: str
) -> None:

    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    # Get extension and skip if unsupported
    ext = file_path.suffix.lower()

    # Blank ext accounts for directories/folders
    if ext not in ['', '.jpg', '.jpeg', '.mp4', '.png']:
        print(
            f"Skipping EXIF for {file_path} "
            f"for unsupported format: {ext}"
        )
        return

    if ext == '.jpeg':
        ext = 'jpg'

    try:
        exiftool_path = find_dependency("exiftool")
    except DependencyError:
        raise

    try:
        lat_f = float(lat)
        lon_f = float(lon)

        if not (-90 <= lat_f <= 90):
            raise ValueError(f"Latitude {lat_f} out of range [-90, 90]")
        if not (-180 <= lon_f <= 180):
            raise ValueError(f"Longitude {lon_f} out of range [-180, 180]")

    except Exception as e:
        raise ValueError(
            f"Invalid coordinates for '{file_path}' "
            f"({lat}, {lon}). Skipping EXIF: {e}."
        )

    # Base command with common tags
    cmd = [
        exiftool_path,
        f"-CreateDate={date_time_str}",
        f"-ModifyDate={date_time_str}",
        f"-DateTimeOriginal={date_time_str}",
        f"-XMP:GPSLatitude={lat}",
        f"-XMP:GPSLongitude={lon}",
    ]

    # Add format-specific MD tags
    if ext == ".mp4":
        cmd.extend([
            f"-TrackCreateDate={date_time_str}",
            f"-TrackModifyDate={date_time_str}",
            f"-MediaCreateDate={date_time_str}",
            f"-MediaModifyDate={date_time_str}",
            f"-Keys:GPSCoordinates={lat} {lon}",
        ])
    elif ext == '.jpg':
        lat_ref = "N" if float(lat) >= 0 else "S"
        lon_ref = "E" if float(lon) >= 0 else "W"
        cmd.extend([
            f"-GPSLatitude={abs(float(lat))}",
            f"-GPSLatitudeRef={lat_ref}",
            f"-GPSLongitude={abs(float(lon))}",
            f"-GPSLongitudeRef={lon_ref}",
        ])

    cmd.extend(["-overwrite_original", str(file_path)])

    # run exiftool program to update metadata tags on file
    try:
        # Skip when it is a directory
        if len(ext) > 0:
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(
                    f"Exiftool error for {file_path}: "
                    f"{result.stderr.strip()}"
                )

    except Exception as e:
        raise MemorEasyError(
            f"Exiftool failed for {file_path}: {e}"
        )

    try:
        set_file_timestamp(file_path, date_time_str[:-4])

    except Exception as e:
        print(
            f"Warning: Could not set modified-date "
            f"timestamp for {file_path}: {e}."
        )

# =========================================================================== #
