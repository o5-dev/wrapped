"""Builds the data that goes into a card link.

The card has no database: everything it shows is packed into the URL hash,
    https://<you>.github.io/wrapped-bot/#<payload>
and docs/card.js unpacks it again. Keep the field order in sync with decodePayload().
"""
from __future__ import annotations

import base64
import json
from datetime import date

PAYLOAD_VERSION = 1
MAX_SERVER, MAX_CHANNEL, MAX_NAME = 40, 32, 32


def _clip(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def emoji_field(emoji) -> str:
    """'😂' for unicode emoji, ':<id>' for custom server emoji (discord.PartialEmoji / Emoji)."""
    if emoji is None:
        return ""
    if isinstance(emoji, str):
        return emoji
    emoji_id = getattr(emoji, "id", None)
    return f":{emoji_id}" if emoji_id else str(emoji)


def encode_card(
    *,
    server: str,
    channel: str,
    total: int,
    name: str,
    user_id: int | str | None = None,
    avatar_hash: str | None = None,
    emoji=None,
    days: int = 30,
    end: date | None = None,
) -> str:
    """Return the payload string (the part after '#').

    name         display name of the top chatter, without the '@'
    user_id      discord user id (kept as a string, snowflakes are too big for JS numbers)
    avatar_hash  discord.py: user.avatar.key, or None for a default avatar
    """
    end = end or date.today()
    data = [
        PAYLOAD_VERSION,
        _clip(server, MAX_SERVER),
        _clip(channel, MAX_CHANNEL),
        int(days),
        end.isoformat(),
        int(total),
        _clip(name, MAX_NAME),
        str(user_id or ""),
        avatar_hash or "",
        emoji_field(emoji),
    ]
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def share_url(base: str, payload: str) -> str:
    """base is the GitHub Pages URL of the docs/ folder (same value as SHARE_BASE in docs/config.js)."""
    return base.rstrip("/") + "/#" + payload
