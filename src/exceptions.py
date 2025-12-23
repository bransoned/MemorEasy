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
class VideoProcessingError(MemorEasyError):
    """Raise when video processing fails"""
    pass
class ZipExtractionError(MemorEasyError):
    """Raised when ZIP extraction or processing fails"""
    pass

# =========================================================================== #
