import base64
import json
from datetime import date


def clip(text, limit):
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit - 1] + "…"


def emoji_field(emoji):
    if emoji is None:
        return ""
    if isinstance(emoji, str):
        return emoji
    if getattr(emoji, "id", None):
        return ":" + str(emoji.id)
    return str(emoji)


def encode_card(server, channel, total, name, user_id=None, avatar_hash=None, emoji=None, days=30, end=None):
    if end is None:
        end = date.today()
    data = [
        1,
        clip(server, 40),
        clip(channel, 32),
        int(days),
        end.isoformat(),
        int(total),
        clip(name, 32),
        str(user_id or ""),
        avatar_hash or "",
        emoji_field(emoji),
    ]
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def share_url(base, payload):
    return base + "#" + payload
