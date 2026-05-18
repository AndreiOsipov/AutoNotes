from pathlib import Path

ROOT_DIR = Path.cwd()
VIDEO_DIR = ROOT_DIR / "subtitles" / "dir_video"
AUDIO_DIR = ROOT_DIR / "subtitles" / "dir_audio"
TEXT_DIR = ROOT_DIR / "subtitles" / "dir_text"
IMAGES_DIR = ROOT_DIR / "subtitles" / "parsed_images"
SUMMARY_POSTFIX = "summary.json"
ENV_FILE = ROOT_DIR / ".env.example"
