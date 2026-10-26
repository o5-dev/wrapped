"""Run with:  python -m pytest tests   (or just: python tests/test_scan.py)"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discord

from bot.cardlink import emoji_field
from bot.scan import scan

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def msg(author, hours_ago, *, bot=False, reactions=(), type=discord.MessageType.default, webhook=None):
    return NS(
        created_at=NOW - timedelta(hours=hours_ago),
        type=type,
        webhook_id=webhook,
        author=NS(id=author, bot=bot, display_name=f"user{author}", avatar=NS(key=f"hash{author}")),
        reactions=[NS(emoji=e, count=c) for e, c in reactions],
    )


async def stream(items):
    for m in items:
        yield m


def run(items, **kw):
    return asyncio.run(scan(stream(items), now=NOW, **kw))


def test_counts_top_chatter_and_emoji():
    custom = discord.PartialEmoji(name="pog", id=1234567890)
    r = run([
        msg(1, 1, reactions=[("😂", 3)]),
        msg(2, 2, reactions=[("😂", 1), (custom, 5)]),
        msg(2, 3),
        msg(2, 4),
        msg(1, 5),
    ], days=30)
    top, n = r.tally.top_chatter()
    assert r.tally.total == 5 and top.id == 2 and n == 3 and top.name == "user2"
    assert top.avatar_key == "hash2"
    assert r.tally.favorite_emoji() == ":1234567890"          # 5 beats 4 (😂)
    assert not r.truncated and r.covered_days == 30


def test_ignores_bots_webhooks_and_system_messages():
    r = run([
        msg(9, 1, bot=True),
        msg(8, 1, webhook=555),
        msg(7, 1, type=discord.MessageType.new_member),
        msg(1, 1, type=discord.MessageType.reply),
    ], days=30)
    assert r.tally.total == 1 and r.tally.top_chatter()[0].id == 1


def test_stops_at_cutoff():
    r = run([msg(1, 24), msg(1, 24 * 5), msg(1, 24 * 40), msg(1, 24 * 50)], days=30)
    assert r.tally.total == 2 and r.scanned == 2


def test_cap_shortens_the_window():
    r = run([msg(1, h) for h in range(1, 101)], days=30, max_messages=48)
    assert r.truncated and r.scanned == 48
    assert r.covered_days == 2                                  # 48 h back -> 2 days


def test_empty_and_no_reactions():
    r = run([], days=30)
    assert r.tally.top_chatter() is None and r.tally.favorite_emoji() is None
    r = run([msg(1, 1)], days=30)
    assert r.tally.favorite_emoji() is None


def test_tie_goes_to_lower_id_and_newest_name_wins():
    first = msg(5, 1); first.author.display_name = "new name"
    old = msg(5, 2); old.author.display_name = "old name"
    r = run([first, old, msg(3, 3), msg(3, 4)], days=30)
    top, _ = r.tally.top_chatter()
    assert top.id == 3
    r = run([first, old], days=30)
    assert r.tally.top_chatter()[0].name == "new name"


def test_progress_callback():
    seen = []

    async def progress(n):
        seen.append(n)

    run([msg(1, 1) for _ in range(1200)], days=30, progress=progress)
    assert seen == [500, 1000]


def test_emoji_field():
    assert emoji_field("😂") == "😂"
    assert emoji_field(discord.PartialEmoji(name="x", id=42)) == ":42"
    assert emoji_field(discord.PartialEmoji(name="👍")) == "👍"
    assert emoji_field(None) == ""


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
