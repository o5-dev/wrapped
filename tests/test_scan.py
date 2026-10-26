import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discord

from bot.cardlink import emoji_field
from bot.scan import scan

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def make_message(author, hours_ago, bot=False, reactions=(), kind=discord.MessageType.default, webhook=None):
    return SimpleNamespace(
        created_at=NOW - timedelta(hours=hours_ago),
        type=kind,
        webhook_id=webhook,
        author=SimpleNamespace(id=author, bot=bot, display_name="user" + str(author), avatar=SimpleNamespace(key="hash" + str(author))),
        reactions=[SimpleNamespace(emoji=emoji, count=count) for emoji, count in reactions],
    )


async def stream(items):
    for item in items:
        yield item


def run(items, **options):
    return asyncio.run(scan(stream(items), now=NOW, **options))


def test_counts_top_chatter_and_emoji():
    custom = discord.PartialEmoji(name="pog", id=1234567890)
    result = run([
        make_message(1, 1, reactions=[("😂", 3)]),
        make_message(2, 2, reactions=[("😂", 1), (custom, 5)]),
        make_message(2, 3),
        make_message(2, 4),
        make_message(1, 5),
    ], days=30)
    top, count = result.tally.top_chatter()
    assert result.tally.total == 5
    assert top.id == 2 and count == 3 and top.name == "user2"
    assert top.avatar_key == "hash2"
    assert result.tally.favorite_emoji() == ":1234567890"
    assert not result.truncated and result.covered_days == 30


def test_ignores_bots_webhooks_and_system_messages():
    result = run([
        make_message(9, 1, bot=True),
        make_message(8, 1, webhook=555),
        make_message(7, 1, kind=discord.MessageType.new_member),
        make_message(1, 1, kind=discord.MessageType.reply),
    ], days=30)
    assert result.tally.total == 1
    assert result.tally.top_chatter()[0].id == 1


def test_stops_at_cutoff():
    result = run([make_message(1, 24), make_message(1, 24 * 5), make_message(1, 24 * 40), make_message(1, 24 * 50)], days=30)
    assert result.tally.total == 2 and result.scanned == 2


def test_cap_shortens_the_window():
    result = run([make_message(1, hours) for hours in range(1, 101)], days=30, max_messages=48)
    assert result.truncated and result.scanned == 48
    assert result.covered_days == 2


def test_empty_and_no_reactions():
    result = run([], days=30)
    assert result.tally.top_chatter() is None
    assert result.tally.favorite_emoji() is None
    result = run([make_message(1, 1)], days=30)
    assert result.tally.favorite_emoji() is None


def test_tie_goes_to_lower_id_and_newest_name_wins():
    newest = make_message(5, 1)
    newest.author.display_name = "new name"
    older = make_message(5, 2)
    older.author.display_name = "old name"
    result = run([newest, older, make_message(3, 3), make_message(3, 4)], days=30)
    assert result.tally.top_chatter()[0].id == 3
    result = run([newest, older], days=30)
    assert result.tally.top_chatter()[0].name == "new name"


def test_progress_callback():
    seen = []

    async def progress(count):
        seen.append(count)

    run([make_message(1, 1) for _ in range(1200)], days=30, progress=progress)
    assert seen == [500, 1000]


def test_emoji_field():
    assert emoji_field("😂") == "😂"
    assert emoji_field(discord.PartialEmoji(name="x", id=42)) == ":42"
    assert emoji_field(discord.PartialEmoji(name="👍")) == "👍"
    assert emoji_field(None) == ""


if __name__ == "__main__":
    for name, function in list(globals().items()):
        if name.startswith("test_"):
            function()
            print("ok", name)
