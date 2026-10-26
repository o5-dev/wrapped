import math
from datetime import timedelta

import discord

from .cardlink import emoji_field
from .stats import Tally

REAL_MESSAGES = [discord.MessageType.default, discord.MessageType.reply]


class ScanResult:
    def __init__(self, tally, scanned, covered_days, truncated):
        self.tally = tally
        self.scanned = scanned
        self.covered_days = covered_days
        self.truncated = truncated


async def scan(messages, days, max_messages=20000, now=None, progress=None):
    if now is None:
        now = discord.utils.utcnow()
    cutoff = now - timedelta(days=days)
    tally = Tally()
    scanned = 0
    oldest = None
    truncated = False

    async for message in messages:
        if message.created_at < cutoff:
            break
        if scanned >= max_messages:
            truncated = True
            break
        scanned += 1
        oldest = message.created_at

        is_person = not message.author.bot and message.webhook_id is None
        if message.type in REAL_MESSAGES and is_person:
            avatar = message.author.avatar
            avatar_key = None
            if avatar:
                avatar_key = avatar.key
            reactions = []
            for reaction in message.reactions:
                reactions.append((emoji_field(reaction.emoji), reaction.count))
            tally.add(message.author.id, message.author.display_name, avatar_key, reactions)

        if progress and scanned % 500 == 0:
            await progress(scanned)

    covered_days = days
    if truncated and oldest is not None:
        covered_days = max(1, math.ceil((now - oldest).total_seconds() / 86400))
    return ScanResult(tally, scanned, covered_days, truncated)
