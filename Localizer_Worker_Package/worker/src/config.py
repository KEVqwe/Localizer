import os

# Target Languages for localization
TARGET_LANGUAGES = ["de", "es", "fr", "id", "it", "pl", "pt", "ru", "tr"]

# Human-readable names for logging
LANGUAGE_NAMES = {
    "de": "German", "es": "Spanish", "fr": "French",
    "id": "Indonesian", "it": "Italian", "pl": "Polish",
    "pt": "Portuguese", "ru": "Russian", "tr": "Turkish"
}

# Default video resolution if probing fails
DEFAULT_VIDEO_WIDTH = 1080
DEFAULT_VIDEO_HEIGHT = 1920

# Rendering Settings
SUBTITLE_DEFAULT_POSITION = "bottom"

# Path to explicit FFmpeg if Winget installation is found
WINGET_FFMPEG_PATH = r"C:\Users\TU\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
