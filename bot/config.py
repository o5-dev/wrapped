import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

guild_id = os.getenv("DEV_GUILD_ID", "").strip()
DEV_GUILD_ID = int(guild_id) if guild_id.isdigit() else None


def read_share_base():
    try:
        text = (ROOT / "docs" / "config.js").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r'SHARE_BASE\s*=\s*"([^"]*)"', text)
    if match is None:
        return ""
    base = match.group(1)
    if "YOUR-USERNAME" in base:
        return ""
    return base


SHARE_BASE = read_share_base()
