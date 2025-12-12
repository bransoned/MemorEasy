from bs4 import BeautifulSoup
import re
import requests
from pathlib import Path
import piexif
from PIL import Image

import os
from datetime import datetime
import time

"""
TODO Need to take data from downloads and begin writing the relevant exif data next...
if data is a zip, need to unzip and then also write that data into the image(s)

Want to also find a way to unzip the file and then combine the video or jpg with its PNG

At a good start right now, though, with it downloading wayyy faster than the HTML script

Also, need to clean up, compartmentalize, and space out this code into functions/cleaner code

"""

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

def deg_to_dms(deg):
    d = int(abs(deg))
    md = (abs(deg) - d) * 60
    m = int(md)
    sd = (md - m) * 60

    return (
        (d, 1),
        (m, 1),
        (int(sd * 10000), 10000)
    )

# =========================================================================== #

def set_file_timestamp(path, date_time_str):
    # Change modified times to original capture date

    # date_time_str = "YYYY:MM:DD HH:MM:SS"
    dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
    ts = dt.timestamp()

    # Set access and modified times
    os.utime(path, (ts, ts))


# =========================================================================== #

def jpg_exif_write(jpg_path, date_time_str, lat, lon):

    """
    date_time_str = "2025:12:02 18:12:04"
    lat = 40.444803
    lon = -77.34570
    """


    try:
        exif_dict = piexif.load(jpg_path)
    except Exception:
        print("Exception")
        exif_dict = {"0th":{}, "Exif":{}, "GPS":{}, "1st":{}}

    # Date/Time
    exif_dict["0th"][piexif.ImageIFD.DateTime] = date_time_str
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_time_str
    exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_time_str

    # GPS
    lat_ref = "N" if float(lat) >= 0 else "S"
    lon_ref = "E" if float(lon) >= 0 else "W"

    exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_ref
    exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = deg_to_dms(float(lat))

    exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_ref
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = deg_to_dms(float(lon))

    # Write new EXIF data to image file
    exif_bytes = piexif.dump(exif_dict)
    img = Image.open(jpg_path)
    img.save(jpg_path, exif=exif_bytes)

    set_file_timestamp(jpg_path, date_time_str[:-4])

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

        # Find SID value
#        SID_pattern = r"&sid=(.{36})"
#        SID = re.search(SID_pattern, url).group(1)

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

            if ext == ".jpg":
                jpg_exif_write(filepath, line["date"], line["lat"], line["lon"])

    print() # final print to flush buffer and have newline

# =========================================================================== #

if __name__ == "__main__":

    html_text = parse_html()

    memories = parse_snapchat_memories(html_text)

    memory_download(memories)
