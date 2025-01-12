import datetime
import os

import discord
import psutil
from discord.ext import commands

from cogs.osu.shared_state import RequestCounter


async def create_status_embed(bot: commands.Bot) -> discord.Embed:
    """
    Creates a Discord embed displaying the bot's current status.
    """
    # Bot uptime
    uptime = datetime.datetime.now(datetime.UTC) - bot.start_time
    uptime_str = str(uptime).split(".")[0]  # Remove microseconds for a cleaner output

    # Bot memory usage
    memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # in MB
    memory_str = f"{memory:.2f} MB"

    # Bot latency
    latency = round(bot.latency * 1000)  # in ms

    # Embed creation
    embed = discord.Embed(
        title="Bot Status",
        colour=0x00B0F4,
    )

    # Set embed fields with bot info
    embed.add_field(name="📅 Uptime", value=f"`{uptime_str}`", inline=False)

    embed.add_field(
        name="🔴 osu! Requests",
        value=(
            "```"
            f"Total Requests:      {RequestCounter.get_count():>9}\n"
            f"Last Minute:         {RequestCounter.get_last_minute_count():>9}\n"
            f"15-Min Average:      {RequestCounter.average_requests_last_15_minutes():>9}\n"
            "```"
        ),
        inline=False,
    )

    embed.add_field(name="💾 Memory Usage", value=f"`{memory_str}`", inline=True)
    embed.add_field(name="⚡ Latency", value=f"`{latency} ms`", inline=True)
    embed.add_field(name="🌐 Servers", value=f"`{len(bot.guilds)}`", inline=True)

    # Footer with bot version
    embed.timestamp = datetime.datetime.now(datetime.UTC)
    embed.set_footer(text="\u200b")

    return embed
