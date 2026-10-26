"""Reads a channel's history (newest first) and feeds a Tally. Needs no privileged intents:
it only looks at authors, timestamps and reactions, never at message content."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import AsyncIterator, Awaitable, Callable

import discord

from .cardlink import emoji_field
from .stats import Tally

# Only real conversation counts: not joins, pins, boosts, thread-created notices, ...
COUNTED_TYPES = {discord.MessageType.default, discord.MessageType.reply}


@dataclass
class ScanResult:
    tally: Tally
    scanned: int          # messages read from Discord (bots included)
    covered_days: int     # window the numbers really cover (shorter than asked if the cap was hit)
    truncated: bool


async def scan(
    messages: AsyncIterator,
    *,
    days: int,
    max_messages: int = 20_000,
    now: datetime | None = None,
    progress: Callable[[int], Awaitable[None]] | None = None,
) -> ScanResult:
    now = now or discord.utils.utcnow()
    cutoff = now - timedelta(days=days)
    tally = Tally()
    scanned = 0
    oldest = None
    truncated = False

    async for m in messages:
        if m.created_at < cutoff:
            break
        if scanned >= max_messages:
            truncated = True
            break
        scanned += 1
        oldest = m.created_at

        if m.type in COUNTED_TYPES and not m.author.bot and m.webhook_id is None:
            avatar = m.author.avatar            # global avatar (the card builds the CDN link from it)
            tally.add(
                m.author.id,
                m.author.display_name,
                avatar.key if avatar else None,
                [(emoji_field(r.emoji), r.count) for r in m.reactions],
            )

        if progress and scanned % 500 == 0:
            await progress(scanned)

    covered = days
    if truncated and oldest is not None:
        covered = max(1, math.ceil((now - oldest).total_seconds() / 86400))
    return ScanResult(tally, scanned, covered, truncated)
