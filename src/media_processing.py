from moviepy import VideoFileClip
from .dependencies import *
from .exceptions import *
from pathlib import Path
from PIL import Image
import subprocess
import os

# =========================================================================== #

"""
Overlay PNG layer onto JPG image

Args:
    jpg_path: Path to base JPG image (must end with "-main.jpg")
    png_path: Path to overlay PNG

Returns:
    Path to combined image (ends with "-combined.jpg")

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
            raise ImageProcessingError(f"Failed to open PNG {png_path.name}: {e}")

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
