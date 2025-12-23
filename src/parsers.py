from .exceptions import *
from .validators import *
from bs4 import BeautifulSoup
import re

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

                except (ValueError, TypeError):
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

            memories.append({
                "date": date_str,
                "type": media_type,
                "lat": lat,
                "lon": lon,
                "url": link
            })

        # Skip any malformed rows that throw error
        except Exception:
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
