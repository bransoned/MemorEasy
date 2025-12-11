from bs4 import BeautifulSoup
import re
import requests
from pathlib import Path

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

def memory_download(memories):

    total_files = len(memories)
    download_count = 1

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

    print() # final print to flush buffer and have newline

# =========================================================================== #

if __name__ == "__main__":

    html_text = parse_html()

    memories = parse_snapchat_memories(html_text)

    memory_download(memories)
