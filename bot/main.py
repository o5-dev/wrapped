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

MAX_MESSAGES = 20000


class WrappedBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.renderer = CardRenderer()
        self.busy_channels = set()

    async def setup_hook(self):
        await self.renderer.start()
        if config.DEV_GUILD_ID:
            guild = discord.Object(config.DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        logging.info("Logged in as %s in %d server(s)", self.user, len(self.guilds))
        if config.SHARE_BASE == "":
            logging.warning("SHARE_BASE in docs/config.js is not set, cards will have no working link")

    async def close(self):
        await self.renderer.close()
        await super().close()


bot = WrappedBot()


async def make_card(interaction, target, days):
    last_edit = 0.0

    async def progress(count):
        nonlocal last_edit
        if time.monotonic() - last_edit < 4:
            return
        last_edit = time.monotonic()
        try:
            await interaction.edit_original_response(content="Reading " + target.mention + "... " + format(count, ",") + " messages so far")
        except discord.HTTPException:
            pass

    result = await scan(target.history(limit=None), days, MAX_MESSAGES, progress=progress)
    top = result.tally.top_chatter()
    if top is None:
        return None

    chatter = top[0]
    payload = encode_card(
        server=interaction.guild.name,
        channel=target.name,
        total=result.tally.total,
        name=chatter.name,
        user_id=chatter.id,
        avatar_hash=chatter.avatar_key,
        emoji=result.tally.favorite_emoji(),
        days=result.covered_days,
    )
    png = await bot.renderer.render(payload)

    link = None
    if config.SHARE_BASE:
        link = share_url(config.SHARE_BASE, payload)

    note = None
    if result.truncated:
        note = "-# I stop at " + format(MAX_MESSAGES, ",") + " messages, so this card covers the last " + str(result.covered_days) + " day(s)."
    return png, link, note


@bot.tree.command(name="wrapped", description="Make a stats card for a channel")
@app_commands.guild_only()
@app_commands.checks.cooldown(1, 60.0, key=lambda interaction: interaction.user.id)
@app_commands.describe(channel="Channel to look at (default: this one)", days="How many days back, 1 to 90 (default 30)")
async def wrapped(
    interaction: discord.Interaction,
    channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
    days: app_commands.Range[int, 1, 90] = 30,
):
    target = channel or interaction.channel
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("I can only look at text channels and threads.", ephemeral=True)
        return

    yours = target.permissions_for(interaction.user)
    if not (yours.view_channel and yours.read_message_history):
        await interaction.response.send_message("You can't read " + target.mention + ", so I can't make a card for it.", ephemeral=True)
        return

    mine = target.permissions_for(interaction.guild.me)
    if not (mine.view_channel and mine.read_message_history):
        await interaction.response.send_message("I need View Channel and Read Message History in " + target.mention + ".", ephemeral=True)
        return

    if target.id in bot.busy_channels:
        await interaction.response.send_message("I'm already reading " + target.mention + ", give me a moment.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    bot.busy_channels.add(target.id)
    try:
        made = await make_card(interaction, target, days)
        if made is None:
            await interaction.edit_original_response(content="No messages from people in " + target.mention + " in the last " + str(days) + " days.")
            return

        png, link, note = made
        view = discord.utils.MISSING
        if link and len(link) <= 512:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Open card", url=link))
        picture = discord.File(io.BytesIO(png), filename="wrapped-" + target.name + ".png")
        await interaction.edit_original_response(content=note, attachments=[picture], view=view)
    except Exception:
        logging.exception("wrapped failed")
        try:
            await interaction.edit_original_response(content="Something went wrong making that card. Try again in a bit.")
        except discord.HTTPException:
            pass
    finally:
        bot.busy_channels.discard(target.id)


@wrapped.error
async def wrapped_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message("Please wait " + str(int(error.retry_after) + 1) + " seconds before using this again.", ephemeral=True)
    else:
        logging.error("command error: %s", error)


def main():
    logging.basicConfig(level=logging.INFO)
    if config.TOKEN == "":
        raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and paste your bot token.")
    bot.run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
