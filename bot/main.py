"""The bot: /wrapped [channel] [days]  ->  card PNG + "Open card" button."""
from __future__ import annotations

import io
import logging
import time
from typing import Optional, Union

import discord
from discord import app_commands

from . import config
from .cardlink import encode_card, share_url
from .render import CardRenderer
from .scan import scan

log = logging.getLogger("wrapped")

MAX_MESSAGES = 20_000          # per scan; a busier channel gets a shorter window instead of a 10 minute wait
CACHE_TTL = 15 * 60            # same channel + days within 15 minutes is served from memory
CACHE_MAX = 50
BUTTON_URL_MAX = 512           # Discord's limit for link buttons

Readable = Union[discord.TextChannel, discord.Thread]


class WrappedBot(discord.Client):
    def __init__(self, settings: config.Settings):
        intents = discord.Intents.none()
        intents.guilds = True                  # no privileged intents needed
        super().__init__(intents=intents)
        self.settings = settings
        self.tree = app_commands.CommandTree(self)
        self.renderer = CardRenderer()
        self.busy: set[int] = set()            # channels being scanned right now
        self.cache: dict[tuple[int, int], tuple[float, bytes, Optional[str], str]] = {}

    async def setup_hook(self) -> None:
        await self.renderer.start()
        if self.settings.dev_guild_id:         # instant while developing; global sync can take a while
            guild = discord.Object(self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("Logged in as %s in %d server(s)", self.user, len(self.guilds))
        if not self.settings.share_base:
            log.warning("SHARE_BASE in docs/config.js is not set: cards will have no working link/QR yet")

    async def close(self) -> None:
        await self.renderer.close()
        await super().close()

    def cache_put(self, key, png: bytes, url: Optional[str], note: str) -> None:
        if len(self.cache) >= CACHE_MAX:
            self.cache.pop(min(self.cache, key=lambda k: self.cache[k][0]))
        self.cache[key] = (time.monotonic(), png, url, note)

    def cache_get(self, key):
        hit = self.cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_TTL:
            return hit[1:]
        return None


def build_bot() -> WrappedBot:
    bot = WrappedBot(config.load())

    @bot.tree.command(name="wrapped", description="Make a stats card for a channel's last 30 days")
    @app_commands.guild_only()
    @app_commands.describe(
        channel="Channel to look at (default: this one)",
        days="How many days back, 1-90 (default 30)",
    )
    async def wrapped(
        interaction: discord.Interaction,
        channel: Optional[Readable] = None,
        days: app_commands.Range[int, 1, 90] = 30,
    ):
        target = channel or interaction.channel
        if not isinstance(target, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message(
                "I can only look at text channels and threads.", ephemeral=True)

        # People may only get stats for channels they can read themselves.
        theirs = target.permissions_for(interaction.user)
        if not (theirs.view_channel and theirs.read_message_history):
            return await interaction.response.send_message(
                f"You can't read {target.mention}, so I can't make a card for it.", ephemeral=True)
        mine = target.permissions_for(interaction.guild.me)
        if not (mine.view_channel and mine.read_message_history):
            return await interaction.response.send_message(
                f"I need **View Channel** and **Read Message History** in {target.mention}.", ephemeral=True)
        if target.id in bot.busy:
            return await interaction.response.send_message(
                f"I'm already reading {target.mention}, give me a moment.", ephemeral=True)

        await interaction.response.defer(thinking=True)
        key = (target.id, days)
        try:
            cached = bot.cache_get(key)
            if cached:
                png, url, note = cached
            else:
                bot.busy.add(target.id)
                try:
                    png, url, note = await make_card(bot, interaction, target, days)
                finally:
                    bot.busy.discard(target.id)
                if png is None:                      # nothing to show, message already sent
                    return
                bot.cache_put(key, png, url, note)

            view = discord.utils.MISSING
            if url and len(url) <= BUTTON_URL_MAX:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Open card", url=url))
            await interaction.edit_original_response(
                content=note or None,
                attachments=[discord.File(io.BytesIO(png), filename=f"wrapped-{target.name}.png")],
                view=view,
            )
        except Exception:
            log.exception("wrapped failed")
            try:
                await interaction.edit_original_response(content="Something went wrong making that card. Try again in a bit.")
            except discord.HTTPException:
                pass

    return bot


async def make_card(bot: WrappedBot, interaction: discord.Interaction, target: Readable, days: int):
    """Scan, count, render. Returns (png, link or None, note) or (None, None, "") if there was nothing to show."""
    last_edit = 0.0

    async def progress(n: int) -> None:
        nonlocal last_edit
        if time.monotonic() - last_edit < 4:         # don't spam edits
            return
        last_edit = time.monotonic()
        try:
            await interaction.edit_original_response(content=f"Reading {target.mention}… {n:,} messages so far")
        except discord.HTTPException:
            pass

    result = await scan(target.history(limit=None), days=days, max_messages=MAX_MESSAGES, progress=progress)
    tally = result.tally
    top = tally.top_chatter()
    if top is None:
        await interaction.edit_original_response(
            content=f"No messages from people in {target.mention} in the last {days} days.")
        return None, None, ""

    chatter, _ = top
    payload = encode_card(
        server=interaction.guild.name,
        channel=target.name,
        total=tally.total,
        name=chatter.name,
        user_id=chatter.id,
        avatar_hash=chatter.avatar_key,
        emoji=tally.favorite_emoji(),
        days=result.covered_days,
    )
    png = await bot.renderer.render(payload)
    base = bot.settings.share_base
    url = share_url(base, payload) if base else None
    note = ""
    if result.truncated:
        note = (f"-# I stop at {MAX_MESSAGES:,} messages, so this card covers the last "
                f"{result.covered_days} day{'s' if result.covered_days != 1 else ''}.")
    return png, url, note


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = config.load()
    if not settings.token:
        raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and paste your bot token.")
    build_bot().run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
