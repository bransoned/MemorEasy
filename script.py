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
from src.downloaders import *

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
