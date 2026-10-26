"""Settings. The token comes from .env; the share link is read from docs/config.js
so the web page and the bot can never disagree about it."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _share_base() -> str:
    try:
        text = (ROOT / "docs" / "config.js").read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r'SHARE_BASE:\s*"([^"]*)"', text)
    base = m.group(1) if m else ""
    return "" if (not base or "YOUR-USERNAME" in base) else base


@dataclass(frozen=True)
class Settings:
    token: str
    dev_guild_id: int | None
    share_base: str          # "" until SHARE_BASE is set in docs/config.js


def load() -> Settings:
    guild = os.getenv("DEV_GUILD_ID", "").strip()
    return Settings(
        token=os.getenv("DISCORD_TOKEN", "").strip(),
        dev_guild_id=int(guild) if guild.isdigit() else None,
        share_base=_share_base(),
    )
