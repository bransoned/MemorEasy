from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from PIL import Image
import subprocess
import requests
import shutil
import time
import sys
import re
import os

# =========================================================================== #

class MemorEasyError(Exception):
    """Base exception for MemorEasy errors"""
    pass
class InvalidInputFileError(MemorEasyError):
    """Raised when memories_history.html is missing or invalid"""
    pass
class DependencyError(MemorEasyError):
    """Raised when required tools (exiftool, ffmpeg) are missing"""
    pass
class ParseError(MemorEasyError):
    """ Raised when HTML parsing fails """
    pass
class DownloadError(MemorEasyError):
    """Raised when Memory download fails"""
    pass
class NetworkError(MemorEasyError):
    """Raised when network connection fails"""
    pass
class ImageProcessingError(MemorEasyError):
    """Rased when image processing fails"""
    pass

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

"""
Find exiftool executable

Returns:
    Path to exiftool

Raises:
    DependencyError: If exiftool cannot be found
"""
def find_exiftool() -> str:

    exe_name = "exiftool.exe" if sys.platform.startswith("win") else "exiftool"

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
        f"Exiftool not found. Please install exiftool or use the provided bundled executable."
        f"For further installation instructions, reference the README."
    )

# =========================================================================== #

"""
Find ffmpeg executable.

Returns:
    Path to ffmpeg

Raises:
    DependencyError: If ffmpeg cannot be found
"""
def find_ffmpeg() -> str:

    exe_name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"

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
        f"FFMpeg not found. Please install ffmpeg or use the provided bundled executable."
        f"For further installation instructions, reference the README."
    )

# =========================================================================== #

"""
Parse user-provided HTML file for user-specific image info

Returns:
    html_text: Raw HTML content from memories_history.html
Raises:
    InvalidInputFileError: If HTML structure does not match expected pattern
"""
def parse_html() -> str:
    target_string = "<div id='mem-info-bar'"

    valid_user_file = validate_input_file("./memories_history.html")

    # Read through user file to find relevant image/video data and API links
    html_text = None
    with open(valid_user_file, "r", encoding="utf-8") as file:
        for line in file:
            if target_string in line:
                html_text = line
                break

    # Check that our user info was found, otherwise raise exception
    if html_text is None:
        raise InvalidInputFileError(
            f"{valid_user_file} does not appear to be a Snapchat-provided HTML file."
            f"Missing expected '<div id='mem-info-bar'>' section."
            f"Please reference the README on prerequisites to run this script."
        )

    return html_text

# =========================================================================== #

"""
Parse Snapchat file data and organize relevant metadata + download URLs

Args:
    html_text: Raw HTML content from memories_history.html that contains
               user specific image data
Returns:
    List of Memory dictionaries with keys: date, type, lat, lon, url
Raises:
    ParseError: If HTML structure is invalid or unexpected
"""
def parse_snapchat_memories(html_text) -> list[dict[str, str, str, str, str]]:

    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception as e:
        raise ParseError(f"Failed to parse HTML: {e}")

    table = soup.find("table")
    if not table:
        raise ParseError(
            "No table found in HTML. The memories_history.html file may be corrupted or incorrect."
        )

    rows = soup.find_all("tr")
    if len(rows) < 2:
        raise ParseError(
            "Table has no data rows. The relevant section of memories_history.html file appears to be empty."
        )

    # Skip header row
    data_rows = rows[1:]
    memories = []
    skipped_count = 0

    for row in data_rows:

        cells = row.find_all("td")

        # Must have 4 columns: Date, Type, Location, URL
        if len(cells) < 4:
            skipped_count += 1
            continue

        try:
            # Extract basic text fields
            date_str = cells[0].get_text(strip=True)
            media_type = cells[1].get_text(strip=True)

            if not date_str or not media_type:
                skipped_count += 1
                continue

            # Extract location
            loc_text = cells[2].get_text(strip=True)
            lat, lon = None, None
            if "Latitude" in loc_text:

                # Format: "Latitude, Longitude: 30.445803, -84.31457"
                match = re.search(r"([-0-9.]+),\s*([-0-9.]+)", loc_text)

                if match:
                    lat, lon = match.groups()

                # Validate coords are in valid ranges
                try:
                    lat_f, lon_f = float(lat), float(lon)
                    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
                        lat, lon = None, None

                except (ValueError, TypeError) as e:
                    lat, lon = None, None
                    skipped_count += 1
                    continue

            # Extract URL from onclick attribute
            link_tag = cells[3].find("a")
            link = None

            if link_tag and "onclick" in link_tag.attrs:

                onclick = link_tag["onclick"]

                # Format: downloadMemories('URL', this, true)
                match = re.search(r"downloadMemories\('([^']+)'", onclick)
                if match:
                    link = match.group(1)

            if not link:
                skipped_count += 1
                continue

            memories.append({
                "date": date_str,
                "type": media_type,
                "lat": lat,
                "lon": lon,
                "url": link
            })

        # Skip any malformed rows that throw error
        except Exception as e:
            skipped_count += 1
            continue

    if not memories:
        raise ParseError(
            "No valid Memories found. The relevant contents in the file may be empty or in unexpected format."
        )

    if skipped_count > 0:
        print(f"Skipped {skipped_count} invalid row(s)")

    print(f"Found {len(memories)} valid memories")
    return memories

# =========================================================================== #

"""
Change the "modified date" in EXIF section to "created date" value

Args:
    path: File path of the file/directory to be edited
    date_time_str: Date to be written to file in format "YYYY-MM-DD HH:MM:SS" in UTC

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
    except ValueError as e:
        raise ValueError(
            f"Invalid date format '{date_time_str}'."
            f"Expected 'YYYY-MM-DD HH:MM:SS'. Error: {e}"
        )

    # Convert to timestamp
    try:
        ts = dt.timestamp()
    except (ValueError, OSErrror) as e:
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
def write_exif(file_path: Path, date_time_str: str, lat: str, lon: str) -> None:

    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get extension and skip if unsupported
    ext = file_path.suffix.lower()

    # Blank ext accounts for directories/folders
    if ext not in ['', '.jpg', '.jpeg', '.mp4', '.png']:
        print(f"Skipping EXIF for {file_path} for unsupported format: {ext}")
        return

    if ext == '.jpeg':
        ext = 'jpg'

    try:
        exiftool_path = find_exiftool()
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
        raise ValueError(f"Invalid coordinates for '{file_path}' ({lat}, {lon}). Skipping EXIF: {e}.")

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
                print(f"Exiftool error for {file_path}: {result.stderr.strip()}")

    except Exception as e:
        raise MemorEasyError(f"Exiftool failed for {file_path}: {e}")

    try:
        set_file_timestamp(file_path, date_time_str[:-4])

    except Exception as e:
        print(f"Warning: Could not set modified-date timestamp for {file_path}: {e}.")

# =========================================================================== #

"""
Overlay PNG layer onto JPG image

Args:
    jpg_path: Path to base JPG image (must end with "-main.jpg")
    png_path: Path to overlay PNG

Returns:
    FileNotFoundError:
    ImageProcessingError:
    ValueError:

Raises:
    FileNotFoundError: If either image file does not exist
    ImageProcessingError: If any various parts of image processing fails
    ValueError: If jpg_path does not end with "-main.jpg"
"""
def merge_jpg_with_overlay(jpg_path: Path, png_path: Path) -> Path:

    if isinstance(jpg_path, str):
        jpg_path = Path(jpg_path)
    if isinstance(png_path, str):
        png_path = Path(png_path)

    # Check that files exist
    if not jpg_path.exists():
        raise FileNotFoundError(f"JPG file not found: {jpg_path}")
    if not png_path.exists():
        raise FileNotFoundError(f"PNG overlay not found: {png_path}")

    # Validate JPG filename format (should be provided by Snap like this)
    if not jpg_path.name.endswith("-main.jpg"):
        raise ValueError(
            f"JPG filename must end with '-main.jpg', got: {jpg_path.name}"
        )

    combined_path = jpg_path.parent / jpg_path.name.replace("-main.jpg", "-combined.jpg")

    if combined_path.exists():
        print(f"Combined image already exists: {combined_path.name}, skipping merge")
        return

    try:

        # Open images
        try:
            base_jpg = Image.open(jpg_path)
        except Exception as e:
            raise ImageProcessingError(f"Failed to open JPG {jpg_path.name}: {e}")
        try:
            overlay = Image.open(png_path)
        except Exception as e:
            raise ImageProcessingError(f"Failed to open PNG {PNG_path.name}: {e}")

        # Validate images loaded properly
        if base_jpg.size[0] == 0 or base_jpg.size[1] == 0:
            raise ImageProcessingError(f"JPG has invalid dimensions {base_jpg.size}")
        if overlay.size[0] == 0 or overlay.size[1] == 0:
            raise ImageProcessingError(f"PNG has invalid dimensions {overlay.size}")

        # Convert JPG to RGBA for compositing
        try:
            if base_jpg.mode != "RGBA":
                base_jpg = base_jpg.convert("RGBA")
        except Exception as e:
            raise ImageProcessingError(f"Failed to convert JPG to RGBA: {e}")

        # Convert PNG to RGBA if needed
        try:
            if overlay.mode != "RGBA":
                overlay = overlay.convert("RGBA")
        except Exception as e:
            raise ImageProcessingError(f"Failed to convert PNG to RGBA: {e}")

        # Resize overlay if dimensions do not match
        if base_jpg.size != overlay.size:
            try:
                overlay = overlay.resize(base_jpg.size, Image.LANCZOS)
            except Exception as e:
                raise ImageProcessingError(f"Failed to resize overlay from {overlay.size} to {base_jpg.size}: {e}")

        # Composite the two images
        try:
            combined = Image.alpha_composite(base_jpg, overlay)
        except Exception as e:
            raise ImageProcessingError(f"Failed to composite images: {e}")

        # Convert JPG back to RGB profile
        try:
            combined = combined.convert("RGB")
        except Exception as e:
            raise ImageProcessingError(f"Failed to convert JPG {jpg_path} to RGB: {e}")


        # Save combined image
        try:
            combined.save(combined_path, "JPEG", quality=95)
        except Exception as e:
            ImageProcessingError(f"Failed to save combined image {combined_path}: {e}")

        # Verify file was created and has size
        if not combined_path.exists():
            raise ImageProcessingError("Combined image was not created")
        if combined_path.stat().st_size == 0:
            combined_path.unlink()  # Delete empty file
            raise ImageProcessingError("Combined image is empty")

        try:
            os.remove(png_path)
        except OSError as e:
            print(f"Warning: Could not delete overlay PNG {png_path.name}: {e}")

        return combined_path

    except ImageProcessingError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise ImageProcessingError(f"Unexpected error merging images: {e}")
    finally:
        # Clean up image objects to free memory
        try:
            if 'base_jpg' in locals():
                base_jpg.close()
            if 'overlay' in locals():
                overlay.close()
            if 'combined' in locals():
                combined.close()
        except Exception:
            pass


# =========================================================================== #

#Overlay PNG layer onto MP4 video
def merge_mp4_with_overlay(mp4_path, png_path) -> Path:

    ffmpeg_path = find_ffmpeg()

    combined_path = mp4_path.replace("-main.mp4", "-combined.mp4")

    # Get mp4 dimensions
    try:
        video = VideoFileClip(mp4_path)
        video_width, video_height = video.size
        video.close()
    except Exception as e:
        print(f"Error reading video dimensions with moviepy: {e}")
        return

    # Resize png file to mp4 dimensions
    try:
        overlay = Image.open(png_path)
        overlay = overlay.resize((video_width, video_height), Image.LANCZOS)
        overlay.save(png_path, "PNG")
    except Exception as e:
        print(f"Error resizing PNG with Pillow: {e}")
        return


    cmd = [
        ffmpeg_path,
        "-i", mp4_path,      # Input video
        "-i", png_path,      # Input overlay
        "-filter_complex", "[0:v][1:v]overlay=0:0",  # Overlay at position 0,0
        "-codec:a", "copy",       # Copy audio without re-encoding
        "-y",                     # Overwrite output file
        combined_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error for {mp4_path}: {result.stderr}")
        return None

    os.remove(png_path)

    return Path(combined_path)

# =========================================================================== #

# Extract files from a zip folder and place them into a new folder matching file naming convention
def handle_zip(filepath, name, line) -> None:

    # Where our extracted images will reside
    new_folder = Path(f"./memories/{name}")

    # Unpack then remove zip file
    shutil.unpack_archive(filepath, new_folder)
    os.remove(filepath)

    have_mp4 = False
    have_jpg = False

    # Go through each file in extracted folder, find and tag mp4/jpg files then the folder
    for file in os.listdir(new_folder):

        zip_file_path = os.path.join(new_folder)

        internal_ext = ""
        if file.endswith("-main.mp4"):
            new_file = f"{name}-main.mp4"
            internal_ext = ".mp4"
            have_mp4 = True

        elif file.endswith("-main.jpg"):
            new_file = f"{name}-main.jpg"
            internal_ext = ".jpg"
            have_jpg = True

        elif file.endswith("-overlay.png"):
            new_file = f"{name}-overlay.png"

        else:
            new_file=file

        # rename zip files from their SID to date/time names
        shutil.move(f"{new_folder}/{file}", f"{new_folder}/{new_file}")

        # If we have a mp4/jpg, write metadata to it
        if internal_ext != "":
            write_exif(Path(f"{new_folder}/{name}-main{internal_ext}"), line["date"], line["lat"], line["lon"])

    # Handles combining main layers with overlay
    if have_mp4:
        combined_path = merge_mp4_with_overlay(f"{new_folder}/{name}-main.mp4", f"{new_folder}/{name}-overlay.png")
        write_exif(combined_path, line["date"], line["lat"], line["lon"])

    if have_jpg:
        combined_path = merge_jpg_with_overlay(f"{new_folder}/{name}-main.jpg", f"{new_folder}/{name}-overlay.png")
        write_exif(combined_path, line["date"], line["lat"], line["lon"])

    # Updates modified time of folder to internal file creation date
    write_exif(new_folder, line["date"], line["lat"], line["lon"])

# =========================================================================== #

"""
Download Memories that are provided in list of dictionaries. Call subfunctions
to handle metadata writing.

Args:
    memories: List of Memory dictionaries with keys: date, type, lat, lon, url

Raises:
    DownloadError: If download fails
    NetworkError: If network connection fails
"""
def memory_download(memories: list[dict[str, str, str, str, str]]) -> None:

    total_files = len(memories)
    if not memories or total_files <= 0:
        print("No memories to download.")
        return

    print(f"\nStarting download of {total_files} memories...\n")

    # Create output directory
    out_dir = Path("./memories")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DownloadError(f"Failed to create output directory: {e}")

    download_count = 0
    failed_downloads = []

    # Logic to begin downloading begins here
    for idx, memory in enumerate(memories):

        url = memory["url"]
        date_str = memory["date"]
        lat = memory["lat"]
        lon = memory["lon"]

        if not url:
            print(f"\nMemory {idx}: No download URL, skipping")
            failed_downloads.append((idx, "No URL"))
            continue

        if not date_str:
            print(f"\nMemory {idx}: No date, skipping")
            failed_downloads.append((idx, "No date"))
            continue
        try:
            # Format: "2025-12-09 11:10:51 UTC" -> "2025-12-09-111051"
            name = date_str.replace(" ", "-")[:-4]
            name = name.replace(":", "")
        except Exception as e:
            print(f"\nMemory {idx}: Invalid date format '{date_str}', skipping")
            failed_downloads.append((idx, f"Invalid date: {e}"))
            continue

        # Implement retries if a download fails
        max_retries = 3
        retry_delay = 2 # seconds

        for attempt in range(0, max_retries):
            try:
                print(f"\rDownloading {idx + 1}/{total_files}: {name}...", end="", flush=True)

                with requests.get(url, stream=True, timeout=30) as r:
                    r.raise_for_status() # Raise exception for 4xx/5xx status codes

                    # Determine file extension from Content-Type header
                    content_type = r.headers.get("Content-Type", "").lower()
                    if "jpg" in content_type:
                        ext = ".jpg"
                    elif "png" in content_type:
                        ext = ".png"
                    elif "mp4" in content_type:
                        ext = ".mp4"
                    elif "zip" in content_type:
                        ext = ".zip"
                    else:
                        print(f"Memory {idx}: Unknown file type '{content_type}', skipping\n")
                        failed_downloads.append((idx, f"Unknown type: {content_type}"))
                        break

                    filepath = out_dir / f"{name}{ext}"
                    filepath_no_ext = out_dir / name

                    if filepath.exists() or filepath_no_ext.exists():
                        print(f"\nMemory {idx}: File already exists, skipping\n")
                        download_count += 1
                        break

                    try:
                        with open(filepath, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192): # 8 KB chunks
                                if chunk: # filter out keep-alive new chunks
                                    f.write(chunk)
                    except OSError as e:
                        raise DownloadError(f"Failed to write file: {e}")

                    if not filepath.exists() or filepath.stat().st_size == 0:
                        raise DownloadError(f"Downloaded file is empty or missing\n")


                # Process the downloaded file
                try:
                    if ext == ".zip":
                        handle_zip(filepath, name, memory)
                    else:
                        write_exif(filepath, date_str, lat, lon)

                except Exception as e:
                    print(f"\nMemory {idx}: Post-processing failed: {e}\n")

                # successful download and processing, move onto next file
                download_count += 1
                break

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(f"\nMemory {idx}: Timeout, retrying ({attempt}/{max_retries})...\n")
                    time.sleep(retry_delay)
                else:
                    print(f"\nMemory {idx}: Timeout after {max_retries} attempts, skipping\n")
                    failed_downloads.append((idx, "Timeout"))

            except requests.exceptions.ConnectionError:
                if attempt < max_retries:
                    print(f"\nMemory {idx}: Connection error, retrying ({attempt}/{max_retries})...\n")
                    time.sleep(retry_delay)
                else:
                    print(f"\nMemory {idx}: Connection failed after {max_retries} attempts, skipping\n")
                    failed_downloads.append((idx, "Connection error"))

            except requests.exceptions.HTTPError as e:
                # Don't retry on 404, 403, etc.
                print(f"\nMemory {idx}: HTTP error {e.response.status_code}, skipping\n")
                failed_downloads.append((idx, f"HTTP {e.response.status_code}"))
                break

            except requests.exceptions.RequestException as e:
                print(f"\nMemory {idx}: Download failed: {e}, skipping\n")
                failed_downloads.append((idx, str(e)))
                break

            except Exception as e:
                print(f"\nMemory {idx}: Unexpected error: {e}, skipping\n")
                failed_downloads.append((idx, str(e)))
                break

    # Final summary
    print(f"\n\n{'='*50}")
    print(f"Successfully downloaded: {download_count}/{total_files}")

    if failed_downloads:
        print(f"Failed downloads: {len(failed_downloads)}")
        print("\nFailed items:")
        for idx, reason in failed_downloads:
            print(f"  - Memory {idx}: {reason}")
    else:
        print("All memories downloaded successfully!")
    print(f"{'='*50}\n")

# =========================================================================== #

def main():

    print(r"""
███╗   ███╗███████╗███╗   ███╗ ██████╗ ██████╗ ███████╗ █████╗ ███████╗██╗   ██╗
████╗ ████║██╔════╝████╗ ████║██╔═══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝╚██╗ ██╔╝
██╔████╔██║█████╗  ██╔████╔██║██║   ██║██████╔╝█████╗  ███████║███████╗ ╚████╔╝
██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║   ██║██╔══██╗██╔══╝  ██╔══██║╚════██║  ╚██╔╝
██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║╚██████╔╝██║  ██║███████╗██║  ██║███████║   ██║
╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝
    """)

    try:
        html_text = parse_html()
        memories = parse_snapchat_memories(html_text)
        memory_download(memories)

    except InvalidInputFileError as e:
        print(f"\nInvalid file: {e}")
        sys.exit(1)
    except ParseError as e:
        print(f"\nParse error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":

    main()
