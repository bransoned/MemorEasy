from .media_processing import (
    write_exif,
    merge_mp4_with_overlay,
    merge_jpg_with_overlay,
    set_file_timestamp
)
from .exceptions import (
    ZipExtractionError,
    DownloadError,
    VideoProcessingError,
    ImageProcessingError,
    DependencyError
)
from pathlib import Path
import requests
import shutil
import time
import os

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


def handle_zip(
    filepath: Path,
    name: str,
    memory: dict[str, str],
) -> None:

    if not filepath.exists():
        raise FileNotFoundError(f"ZIP file not found: {filepath}")

    # Create folder path for extracted files
    new_folder = Path(f"./memories/{name}")

    if new_folder.exists():
        print(
            f"Folder already exists: {new_folder.name}, skipping extraction"
        )

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
        print(
            f"Warning: Could not delete ZIP file {filepath.name}: {e}"
        )

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
                    print(
                         f"Warning: Could not rename {old_name} "
                         f"to {new_name}: {e}"
                    )
                    continue

        # Verify we found expected files
        if not main_mp4 and not main_jpg:
            raise ZipExtractionError(
                f"No main media file found in {filepath.name}. "
                f"Exprected file ending with '-main.mp4' or '-main.jpg'"
            )
        if not overlay_png:
            print(
                f"Warning: No overlay PNG found in "
                f"{filepath.name}"
            )

        # Get Memory metadata values
        date_str = memory["date"]
        lat = memory["lat"]
        lon = memory["lon"]

        # Make sure valid metadata
        if not date_str:
            raise ValueError(
                 f"Date string not found in Memory "
                 f"{filepath.name}."
            )
        if not lat or not lon:
            raise ValueError(
                f"GPS coordinates not found in Memory "
                f"{filepath.name}."
            )

        # Process MP4 if found
        if main_mp4 and main_mp4.exists():
            try:
                # Tag original MP4
                write_exif(main_mp4, date_str, lat, lon)

                if overlay_png and overlay_png.exists():
                    try:
                        combined_path = merge_mp4_with_overlay(
                            main_mp4, overlay_png
                        )
                        write_exif(combined_path, date_str, lat, lon)
                    except (VideoProcessingError, DependencyError) as e:
                        print(
                            f"Warning: Failed to merge MP4 with overlay: {e}"
                        )
                    except Exception as e:
                        print(
                            f"Warning: Unexpected error merging MP4: {e}"
                        )

            except Exception as e:
                print(
                    f"Warning: Failed to process MP4: {e}"
                )

        # Process JPG if found
        if main_jpg and main_jpg.exists():
            try:
                # Tag original JPG
                write_exif(main_jpg, date_str, lat, lon)

                if overlay_png and overlay_png.exists():
                    try:
                        combined_path = merge_jpg_with_overlay(
                            main_jpg, overlay_png
                        )
                        write_exif(combined_path, date_str, lat, lon)
                    except ImageProcessingError as e:
                        print(
                            f"Warning: Failed to merge JPG with overlay: {e}"
                        )
                    except Exception as e:
                        print(
                            f"Warning: Unexpected error merging JPG: {e}"
                        )

            except Exception as e:
                print(
                    f"Warning: Failed to process JPG: {e}"
                )

        # Set folder timestamp to match content
        try:  # not sure this is right
            timestamp_date = date_str.replace(" UTC", "").strip()
            set_file_timestamp(new_folder, timestamp_date)
        except Exception as e:
            print(
                f"Warning: Could not set folder timestamp: {e}"
            )

    except ZipExtractionError:
        #  Re-raise our custom errors
        raise
    except Exception as e:
        #  Catch unexpected errors
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


def memory_download(
    memories: list[dict[str, str]],
) -> None:

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
            print(
                f"\nMemory {idx}: Invalid date format '{date_str}', skipping"
                 )
            failed_downloads.append((idx, f"Invalid date: {e}"))
            continue

        # Implement retries if a download fails
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(0, max_retries):
            try:
                print(
                    f"\rDownloading {idx + 1}/{total_files}: {name}...",
                    end="",
                    flush=True
                )

                with requests.get(url, stream=True, timeout=30) as r:
                    # Raise exception for 4xx/5xx status codes
                    r.raise_for_status()

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
                        print(
                            f"Memory {idx}: Unknown Content-Type"
                            f"'{content_type}', skipping\n"
                        )
                        failed_downloads.append(
                            (idx, f"Unknown type: {content_type}")
                            )
                        break

                    filepath = out_dir / f"{name}{ext}"
                    filepath_no_ext = out_dir / name

                    if filepath.exists() or filepath_no_ext.exists():
                        print(
                            f"\nMemory {idx}: File already exists, skipping\n"
                        )
                        download_count += 1
                        break

                    try:
                        with open(filepath, 'wb') as f:
                            # 8 KB chunks
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:  # filter out keep-alive new chunks
                                    f.write(chunk)
                    except OSError as e:
                        raise DownloadError(f"Failed to write file: {e}")

                    if not filepath.exists() or filepath.stat().st_size == 0:
                        raise DownloadError(
                            "Downloaded file is empty or missing\n"
                        )

                # Process the downloaded file
                try:
                    if ext == ".zip":
                        handle_zip(filepath, name, memory)
                    else:
                        write_exif(filepath, date_str, lat, lon)

                except Exception as e:
                    print(
                        f"\nMemory {idx}: Post-processing failed: {e}\n"
                    )

                # successful download and processing, move onto next file
                download_count += 1
                break

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(
                        f"\nMemory {idx}: Timeout, retrying "
                        f"({attempt}/{max_retries})...\n"
                    )
                    time.sleep(retry_delay)
                else:
                    print(
                        f"\nMemory {idx}: Timeout after {max_retries} "
                        f" attempts, skipping\n"
                    )
                    failed_downloads.append((idx, "Timeout"))

            except requests.exceptions.ConnectionError:
                if attempt < max_retries:
                    print(
                        f"\nMemory {idx}: Connection error, retrying "
                        f"({attempt}/{max_retries})...\n"
                    )
                    time.sleep(retry_delay)
                else:
                    print(
                        f"\nMemory {idx}: Connection failed after "
                        f" {max_retries} attempts, skipping\n"
                    )
                    failed_downloads.append((idx, "Connection error"))

            except requests.exceptions.HTTPError as e:
                # Don't retry on 404, 403, etc.

                # Retry on server errors.
                # This seems to be most prevalent error when downloading
                status = e.response.status_code
                if 500 <= status < 600:
                    if attempt < max_retries:
                        print(
                            f"\nMemory {idx}: Server error {status}, "
                            f"retry attempt {attempt}/{max_retries}"
                        )
                        time.sleep(retry_delay)
                        continue

                print(
                    f"\nMemory {idx}: HTTP error "
                    f"{e.response.status_code}, skipping\n"
                )
                failed_downloads.append(
                    (idx, f"HTTP {e.response.status_code}")
                )
                break

            except requests.exceptions.RequestException as e:
                print(
                    f"\nMemory {idx}: Download failed: {e}, "
                    f"skipping\n"
                )
                failed_downloads.append((idx, str(e)))
                break

            except Exception as e:
                print(
                    f"\nMemory {idx}: Unexpected error: {e}, "
                    f"skipping\n"
                )
                failed_downloads.append((idx, str(e)))
                break

    # Final summary
    print(f"\n\n{'='*50}")
    print(
        f"Successfully downloaded: {download_count}/{total_files}"
    )

    if failed_downloads:
        print(f"Failed downloads: {len(failed_downloads)}")
        print("\nFailed items:")
        for idx, reason in failed_downloads:
            print(f"  - Memory {idx}: {reason}")
    else:
        print("All memories downloaded successfully!")
    print(f"{'='*50}\n")

# =========================================================================== #
