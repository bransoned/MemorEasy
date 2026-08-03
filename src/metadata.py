from datetime import datetime, timezone
from .dependencies import find_dependency
from .exceptions import DependencyError, MemorEasyError
from pathlib import Path
import subprocess
import os

from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder

# =========================================================================== #

"""
Convert UTC datetime string to timezone-aware local datetime
using GPS coordinates.
"""
def utc_str_to_local_dt(
    utc_str: str,
    lat: float,
    lon: float,
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> datetime:

    tf = TimezoneFinder()

    utc_dt = datetime.strptime(utc_str, fmt).replace(tzinfo=timezone.utc)

    tz_name = tf.timezone_at(lat=lat, lng=lon)
    if not tz_name:
        # Fallback to UTC if timezone cannot be determined
        return utc_dt

    return utc_dt.astimezone(ZoneInfo(tz_name))


# =========================================================================== #

"""
Return EXIF offset string like '+05:30' or '-04:00'
from a timezone-aware datetime.
"""

def offset_str_from_dt(dt: datetime) -> str:
    offset = dt.utcoffset()
    if offset is None:
        return "+00:00"

    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"{sign}{hours:02d}:{minutes:02d}"

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


def set_file_timestamp(path, local_dt) -> None:

    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    if local_dt.tzinfo is None:
        raise ValueError("local_dt must be timezone-aware")

    # Validate and parse date string
#    try:
#        ts = local_dt.timestamp()
#        dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
#        dt = dt.replace(tzinfo=timezone.utc)
#    except ValueError as e:
#        raise ValueError(
#            f"Invalid date format '{date_time_str}'."
#            f"Expected 'YYYY-MM-DD HH:MM:SS'. Error: {e}"
#            raise ValueError(f"Cannot convert datetime to timestamp: {e}")
#        )

    # Convert to timestamp
    try:
        ts = local_dt.timestamp()
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

    local_dt = utc_str_to_local_dt(date_time_str[:-4], lat_f, lon_f)
    local_dt_str = local_dt.strftime("%Y-%m-%d %H:%M:%S")
    offset_str = offset_str_from_dt(local_dt)

    # Base command with common tags
    cmd = [
        exiftool_path,
        f"-XMP:GPSLatitude={lat}",
        f"-XMP:GPSLongitude={lon}",
    ]

    # Add format-specific MD tags
    if ext == ".mp4":
        cmd.extend([
            f"-TrackCreateDate={date_time_str[:-4]}",
            f"-TrackModifyDate={date_time_str[:-4]}",
            f"-MediaCreateDate={date_time_str[:-4]}",
            f"-MediaModifyDate={date_time_str[:-4]}",
            f"-Keys:GPSCoordinates={lat} {lon}",
        ])
    elif ext == '.jpg':
        lat_ref = "N" if float(lat) >= 0 else "S"
        lon_ref = "E" if float(lon) >= 0 else "W"
        cmd.extend([
            f"-CreateDate={local_dt_str}",
            f"-ModifyDate={local_dt_str}",
            f"-DateTimeOriginal={local_dt_str}",
            f"-OffsetTime={offset_str}",
            f"-OffsetTimeOriginal={offset_str}",
            f"-OffsetTimeDigitized={offset_str}",
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
        set_file_timestamp(file_path, local_dt)

    except Exception as e:
        print(
            f"Warning: Could not set modified-date "
            f"timestamp for {file_path}: {e}."
        )

# ===========================================================================
