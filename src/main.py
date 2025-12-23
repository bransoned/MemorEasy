import traceback
import sys

from .exceptions import *
from .validators import *
from .dependencies import *
from .parsers import *
from .metadata import *
from .media_processing import *
from .downloaders import *

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

# =========================================================================== #
