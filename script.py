from moviepy import VideoFileClip
#from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from PIL import Image
import subprocess
import traceback
import requests
import shutil
import time
import sys
#import re
import os

from src.exceptions import *
from src.validators import *
from src.dependencies import *
from src.parsers import *
from src.metadata import *
from src.media_processing import *


"""
Overlay PNG layer onto MP4 video

Args:
    mp4_path: Path to base MP4 video (must end with "-main.mp4")
    png_path: Path to overlay PNG

Returns:
    Path to combined video (ends with "-combined.mp4")

Raises:
    FileNotFoundError: If either image file does not exist
    DependencyError: Of ffmpeg not found
    VideoProcessingError: If any various parts of image processing fails
    ValueError: If mp4_path does not end with "-main.mp4"
"""
def merge_mp4_with_overlay(mp4_path: Path, png_path: Path) -> Path:

    # Validate inputs are Path objects
    if isinstance(mp4_path, str):
        mp4_path = Path(mp4_path)
    if isinstance(png_path, str):
        png_path = Path(png_path)

    # Check files exist
    if not mp4_path.exists():
        raise FileNotFoundError(f"MP4 file not found: {mp4_path}")
    if not png_path.exists():
        raise FileNotFoundError(f"PNG overlay not found: {png_path}")

    # Validate MP4 filename format
    if not mp4_path.name.endswith("-main.mp4"):
        raise ValueError(
            f"MP4 filename must end with '-main.mp4', got: {mp4_path.name}"
        )

    combined_path = mp4_path.parent / mp4_path.name.replace("-main.mp4", "-combined.mp4")

    # Check if combined file already exists
    if combined_path.exists():
        print(f"Combined video already exists: {combined_path.name}, skipping merge")
        return combined_path

    # Find ffmpeg dependency
    try:
        ffmpeg_path = find_ffmpeg()
    except DependencyError:
        raise # Re-raise to be handled by caller

    video = None
    overlay = None

    try:
        # Get MP4 dimensions using moviepy
        try:
            video = VideoFileClip(mp4_path)
            video_width, video_height = video.size

            if video_width <= 0 or video_height <= 0:
                raise VideoProcessingError(f"Invalid video dimensions: {video_width}x{video_height}")
        except Exception as e:
            raise VideoProcessingError(f"Failed to read video dimensions from {mp4_path.name}: {e}.")
        finally:
            if video:
                try:
                    video.close()
                except Exception:
                    pass

        # Resize png file to mp4 dimensions
        try:
            overlay = Image.open(png_path)
            overlay = overlay.resize((video_width, video_height), Image.LANCZOS)
            overlay.save(png_path, "PNG")
        except Exception as e:
            raise VideoProcessingError(
                "Failed to resize PNG overlay to "
                f"{video_width}x{video_height}: {e}"
            )
        finally:
            if overlay:
                try:
                    overlay.close()
                except Exception:
                    pass


        cmd = [
            ffmpeg_path,
            "-i", mp4_path,      # Input video
            "-i", png_path,      # Input overlay
            "-filter_complex", "[0:v][1:v]overlay=0:0",  # Overlay at position 0,0
            "-codec:a", "copy",       # Copy audio without re-encoding
            "-y",                     # Overwrite output file
            str(combined_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise VideoProcessingError(f"FFmpeg failed for {mp4_path.name}: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise VideoProcessingError(f"FFmpeg timed out processing {mp4_path.name} (exceeded 5 minutes)")
        except Exception as e:
            raise VideoProcessingError(f"FFmpeg error: {e}")

        # Verify file was created
        if not combined_path.exists():
            raise VideoProcessingError("Combined video was not created")

        # Verify output file not empty
        if combined_path.stat().st_size == 0:
            combined_path.unlink()
            raise VideoProcessingError("Combined video is empty")

        try:
            os.remove(png_path)
        except OSError as e:
            print(f"Warning: Could not delete overlay PNG {png_path.name}: {e}")

        return combined_path

    except VideoProcessingError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise VideoProcessingError(f"Unexpected error merging video with overlay: {e}")

# =========================================================================== #

"""
Extract files from a ZIP folder and process Snapchat memory files

Args:
    filepath: Path to ZIP file
    name: Base name for files (datetime string without extension)
    memory: Memory dictionary with keys: date, type, lat, lon, url

Raises:
    FileNotFoundError: If ZIP file doesn't exist
    ZipExtractionError: If extraction or processing fails
"""
def handle_zip(filepath: Path, name: str, memory: dict[str, str, str, str, str]) -> None:

    if not filepath.exists():
        raise FileNotFoundError(f"ZIP file not found: {filepath}")


    # Create folder path for extracted files
    new_folder = Path(f"./memories/{name}")

    if new_folder.exists():
        print(f"Folder already exists: {new_folder.name}, skipping extraction")

    # Create folder
    try:
        new_folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ZipExtractionError(f"Failed to create folder {new_folder}: {e}.")

    # Extract ZIP
    try:
        shutil.unpack_archive(filepath, new_folder)
    except Exception as e:
        # Cleanup and remove partial extraction if fail
        try:
            shutil.rmtree(new_folder)
        except Exception:
            pass
        raise ZipExtractionError(f"Failed to extract {filepath.name}: {e}")

    # Remove ZIP file after successful extraction
    try:
        os.remove(filepath)
    except OSError as e:
        print(f"Warning: Could not delete ZIP file {filepath.name}: {e}")


    # Track what files we found
    main_mp4 = None
    main_jpg = None
    overlay_png = None

    # Processs extracted files
    try:
        files = list(new_folder.iterdir())

        if not files:
            raise ZipExtractionError(f"ZIP file {filepath.name} was empty")
        for file in files:

            old_name = file.name
            new_name = None

            if old_name.endswith("-main.mp4"):
                new_name = f"{name}-main.mp4"
                main_mp4 = new_folder / new_name
            elif old_name.endswith("-main.jpg"):
                new_name = f"{name}-main.jpg"
                main_jpg = new_folder / new_name
            elif old_name.endswith("-overlay.png"):
                new_name = f"{name}-overlay.png"
                overlay_png = new_folder / new_name
            else:
                # Keep unknown files with original name
                print(f"Unknown file in ZIP: {old_name}, keeping as-is")
                continue

            # Rename file
            if new_name:
                try:
                    new_path = new_folder / new_name
                    file.rename(new_path)
                except OSError as e:
                    print(f"Warning: Could not rename {old_name} to {new_name}: {e}")
                    continue

        # Verify we found expected files
        if not main_mp4 and not main_jpg:
            raise ZipExtractionError(
                f"No main media file found in {filepath.name}. "
                f"Exprected file ending with '-main.mp4' or '-main.jpg'"
            )
        if not overlay_png:
            print(f"Warning: No overlay PNG found in {filepath.name}")

        # Get Memory metadata values
        date_str = memory["date"]
        lat = memory["lat"]
        lon = memory["lon"]

        # Make sure valid metadata
        if not date_str:
            raise ValueError("Date string not found in Memory {filepath.name}.")
        if not lat or not lon:
            raise ValueError("GPS coordinates not found in Memory {filepath.name}.")

        # Process MP4 if found
        if main_mp4 and main_mp4.exists():
            try:
                # Tag original MP4
                write_exif(main_mp4, date_str, lat, lon)

                if overlay_png and overlay_png.exists():
                    try:
                        combined_path = merge_mp4_with_overlay(main_mp4, overlay_png)
                        write_exif(combined_path, date_str, lat, lon)
                    except (VideoProcessingError, DependencyError) as e:
                        print(f"Warning: Failed to merge MP4 with overlay: {e}")
                    except Exception as e:
                        print(f"Warning: Unexpected error merging MP4: {e}")

            except Exception as e:
                print(f"Warning: Failed to process MP4: {e}")

        # Process JPG if found
        if main_jpg and main_jpg.exists():
            try:
                # Tag original JPG
                write_exif(main_jpg, date_str, lat, lon)

                if overlay_png and overlay_png.exists():
                    try:
                        combined_path = merge_jpg_with_overlay(main_jpg, overlay_png)
                        write_exif(combined_path, date_str, lat, lon)
                    except ImageProcessingError as e:
                        print(f"Warning: Failed to merge JPG with overlay: {e}")
                    except Exception as e:
                        print(f"Warning: Unexpected error merging JPG: {e}")

            except Exception as e:
                print(f"Warning: Failed to process JPG: {e}")

        # Set folder timestamp to match content
        try: # not sure this is right
            timestamp_date = date_str.replace(" UTC", "").strip()
            set_file_timestamp(new_folder, timestamp_date)
        except Exception as e:
            print(f"Warning: Could not set folder timestamp: {e}")

    except ZipExtractionError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # Catch unexpected errors
        raise ZipExtractionError(f"Failed to process extracted files: {e}")

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
                        raise DownloadError("Downloaded file is empty or missing\n")


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

                # Retry on server errors. This seems to be most prevalent error when downloading
                status = e.response.status_code
                if 500 <= status < 600:
                    if attempt < max_retries:
                        print(f"\nMemory {idx}: Server error {status}, retry attempt {attempt}/{max_retries}")
                        time.sleep(retry_delay)
                        continue

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
        input("\nPress Enter to exit...")

    except InvalidInputFileError as e:
        print(f"\nInvalid file: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    except ParseError as e:
        print(f"\nParse error: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":

    main()
