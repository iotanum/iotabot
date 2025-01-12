from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

import cogs.osu.client as osu_client
from app.models.discord_users import DiscordUsers
from app.models.scores import Scores
from app.models.user import User
from cogs.utils.score_embed import create_score_embed
from cogs.utils.status_embed import create_status_embed


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Default commands are ready!")

    @app_commands.command(name="status", description="Get the bot's current status.")
    async def status(self, interaction: discord.Interaction):
        """Get the bot's current status."""
        embed = await create_status_embed(self.bot)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ls", description="See your latest osu! score.")
    async def ls(self, interaction: discord.Interaction, user: Optional[str] = None):
        """See your latest osu! score."""
        await interaction.response.defer()

        try:
            # Handle the case where a specific user is provided
            if user:
                await self._handle_user_request(interaction, user)
                return

            # Handle the case for the current Discord user
            await self._handle_discord_user_request(interaction)

        except Exception as e:
            await interaction.followup.send(f"❌ An unexpected error occurred: {e}")

    async def _handle_user_request(self, interaction: discord.Interaction, user: str | int):
        osu_db_user = await User.get(self.bot.db_session, user)
        if osu_db_user:
            await self._send_latest_score(interaction, osu_db_user.user_id)
            return

        osu_api_user = await osu_client.get_user(user)
        if not osu_api_user:
            await interaction.followup.send(f"❌ User '{user}' not found.")
            return

        score = await osu_client.get_recent_user_score(osu_api_user.id)
        if not score:
            await interaction.followup.send("❌ No scores found.")
            return

        db_score = await Scores.add(self.bot.db_session, score)
        embed = await create_score_embed(self.bot.db_session, db_score)
        await interaction.followup.send(embed=embed)

    async def _handle_discord_user_request(self, interaction: discord.Interaction):
        discord_db_user = await DiscordUsers.get(self.bot.db_session, interaction)
        if not discord_db_user:
            await interaction.followup.send(
                "❌ You have not registered your osu! name in the database, use `/osu ls_add` to add it."
            )
            return

        await self._send_latest_score(interaction, discord_db_user.user_id)

    async def _send_latest_score(self, interaction: discord.Interaction, user_id: int):
        latest_score = await Scores.get_latest(self.bot.db_session, user_id=user_id)
        if not latest_score:
            await interaction.followup.send("❌ No scores found.")
            return

        embed = await create_score_embed(self.bot.db_session, latest_score)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
