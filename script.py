from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import subprocess
import requests
import shutil
import time
import sys
import re
import os

"""
TODO Need to take data from downloads and begin writing the relevant exif data next...
if data is a zip, need to unzip and then also write that data into the image(s)

Want to also find a way to unzip the file and then combine the video or jpg with its PNG

At a good start right now, though, with it downloading wayyy faster than the HTML script

Also, need to clean up, compartmentalize, and space out this code into functions/cleaner code

"""

# =========================================================================== #

# Return name/path of exiftool, bundled or system-wide
def find_exiftool():

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

    raise FileNotFoundError(f"Could not find exiftool. Tried bundled and system PATH.")

# =========================================================================== #

# Logic to parse user-provided html file for user-specific image info
def parse_html():
    target_string = "<div id='mem-info-bar'"
    with open("memories_history.html", "r", encoding="utf-8") as file:
        for line in file:
            if target_string in line:
                html_text = line
    return html_text

# =========================================================================== #

def parse_snapchat_memories(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    rows = soup.find_all("tr")[1:]  # skip header row

    memories = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # Extract basic text fields
        date_str = cells[0].get_text(strip=True)
        media_type = cells[1].get_text(strip=True)

        # Extract location
        loc_text = cells[2].get_text(strip=True)
        lat, lon = None, None
        if "Latitude" in loc_text:
            match = re.search(r"([-0-9.]+),\s*([-0-9.]+)", loc_text)
            if match:
                lat, lon = match.groups()

        # Extract URL from onclick attribute
        link_tag = cells[3].find("a")
        link = None

        if link_tag and "onclick" in link_tag.attrs:
            onclick = link_tag["onclick"]
            # Extract the URL inside downloadMemories('URL', ...)
            match = re.search(r"downloadMemories\('([^']+)'", onclick)
            if match:
                link = match.group(1)

        memories.append({
            "date": date_str,
            "type": media_type,
            "lat": lat,
            "lon": lon,
            "url": link
        })

    return memories

# =========================================================================== #

def set_file_timestamp(path, date_time_str):
    # Change modified times to original capture date

    # date_time_str = "YYYY:MM:DD HH:MM:SS"
    dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
    ts = dt.timestamp()

    # Set access and modified times
    os.utime(path, (ts, ts))

# =========================================================================== #

def write_exif(file_path, date_time_str, lat, lon, ext):
    """
    date_time_str = "2025:12:02 18:12:04"
    lat = 40.444803
    lon = -77.34570
    """

    exiftool_path = find_exiftool()

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

    # run exiftool program to update md tags on file
    result = 0
    if len(ext) > 0:
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result and result.returncode != 0:
        print(f"Exiftool error for {file_path}: {result.stderr}")

    set_file_timestamp(file_path, date_time_str[:-4])

# =========================================================================== #

# Extract files from a zip folder and place them into a new folder matching file naming convention
def handle_zip(filepath, name, line):

    # Where our extracted images will reside
    new_folder = f"./memories/{name}"

    # Unpack then remove zip file
    shutil.unpack_archive(filepath, new_folder)
    os.remove(filepath)

    # Go through each file in extracted folder, find and tag mp4/jpg files then the folder
    for file in os.listdir(new_folder):

        zip_file_path = os.path.join(new_folder)

        internal_ext = ""
        if file.endswith("-main.mp4"):
            new_file = f"{name}-main.mp4"
            internal_ext = ".mp4"
        elif file.endswith("-main.jpg"):
            new_file = f"{name}-main.jpg"
            internal_ext = ".jpg"
        elif file.endswith("-overlay.png"):
            new_file = f"{name}-overlay.png"
        else:
            new_file=file

        # rename zip files from their SID to date/time names
        shutil.move(f"{new_folder}/{file}", f"{new_folder}/{new_file}")

        # If we have a mp4/jpg, write metadata to it
        if internal_ext != "":
            write_exif(f"{new_folder}/{name}-main{internal_ext}", line["date"], line["lat"], line["lon"], internal_ext)

        # Updates modified time of folder to internal file creation date
        write_exif(new_folder, line["date"], line["lat"], line["lon"], "")

    # TODO Combine png layer with jpg file. Save as separate file to preserve blank jpg
    # Delete png after that

# =========================================================================== #

def memory_download(memories):

    total_files = len(memories)
    download_count = 1

    if total_files <= 0:
        print("No memories found.")
        return

    # Logic to begin downloading begins here
    for line in memories:

        url = line["url"]
        name = line["date"]

        name = name.replace(" ", "-")[:-4]
        name = name.replace(":", "")

        with requests.get(url, stream=True) as r:
            r.raise_for_status()

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
                ext = ""  # fallback

            out_dir = Path("./memories") # TODO give option for user-defined path in future
            out_dir.mkdir(parents=True, exist_ok=True)

            filepath = out_dir / f"{name}{ext}"

            print(f"\rDownloading {download_count}/{total_files}...", end="", flush=True)

            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): # 8 KB chunks
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
            download_count += 1

            # Handle file operations for memories provided in zip folders
            if ext == ".zip":
                handle_zip(filepath, name, line)

            # Normal JPG or MP4 provided to us
            else:
                write_exif(filepath, line["date"], line["lat"], line["lon"], ext)

    print() # final print to flush buffer and have newline

# =========================================================================== #

if __name__ == "__main__":

    html_text = parse_html()

    memories = parse_snapchat_memories(html_text)

    memory_download(memories)
