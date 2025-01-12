import discord
from discord import app_commands
from discord.ext import commands

import cogs.osu.client as osu_client
from app.models.discord_users import DiscordUsers
from app.models.tracking_channels import TrackingChannels
from app.models.user import User
from cogs.utils.user_embed import create_user_embed


class OsuGroup(commands.Cog):
    name = "osu"
    description = "Group of commands related to osu!"
    command_group = app_commands.Group(name=name, description=description)

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("OsuGroup is ready!")

    @command_group.command(name="user")
    @app_commands.describe(user_id="The ID of the user you want to get.")
    async def user(self, interaction: discord.Interaction, user_id: int):
        """Get a user by their ID."""
        await interaction.response.defer()
        user = await osu_client.get_user(user_id)

        if not user:
            await interaction.followup.send(f"❌ User with ID `{user_id}` not found.")
            return

        user_embed, view = await create_user_embed(user)
        await interaction.followup.send(embed=user_embed, view=view)

    @command_group.command(name="track")
    @app_commands.describe(user="The ID or Username of the user you want to track.")
    async def track(self, interaction: discord.Interaction, user: str):
        """Start tracking a user in this channel."""
        await interaction.response.defer()

        # Check if user is in the database
        db_user = await User.get(self.bot.db_session, user)
        if not db_user:
            api_user = await osu_client.get_user(user)
            if not api_user:
                await interaction.followup.send(f"❌ User '{user}' not found.")
                return
            await User.add(self.bot.db_session, api_user)
            db_user = await User.get(self.bot.db_session, user)

        # Check if already tracked in the current channel
        track_list = await TrackingChannels.get(
            self.bot.db_session, db_user.user_id, interaction
        )
        if any(track.channel_id == interaction.channel_id for track in track_list):
            await interaction.followup.send(
                f"❌ User '{db_user.username}' is already being tracked in this channel."
            )
            return

        # Add tracking
        await TrackingChannels.add(self.bot.db_session, db_user.user_id, interaction)
        await interaction.followup.send(
            f"✅ User '{db_user.username}' ({db_user.user_id}) is now being tracked in "
            f"'{interaction.channel.name}' on '{interaction.guild.name}'."
        )

    @command_group.command(name="untrack")
    @app_commands.describe(user="The ID or Username of the user you want to untrack.")
    async def untrack(self, interaction: discord.Interaction, user: str):
        """Stop tracking a user in this channel."""
        await interaction.response.defer()

        db_user = await User.get(self.bot.db_session, user)
        if not db_user:
            await interaction.followup.send(
                f"❌ User '{user}' not found in the database."
            )
            return

        tracking = await TrackingChannels.get(
            self.bot.db_session, db_user.user_id, interaction
        )
        if not tracking:
            await interaction.followup.send(
                f"❌ User '{db_user.username}' is not being tracked in this channel."
            )
            return

        await TrackingChannels.delete(self.bot.db_session, db_user.user_id, interaction)
        await interaction.followup.send(
            f"✅ User '{db_user.username}' is no longer being tracked."
        )

    @command_group.command(name="list")
    @app_commands.describe()
    async def list(self, interaction: discord.Interaction):
        """List all users being tracked in this channel."""
        await interaction.response.defer()

        tracking_list = await TrackingChannels.get_by_channel(
            self.bot.db_session, interaction
        )
        if not tracking_list:
            await interaction.followup.send(
                "❌ No users are being tracked in this channel."
            )
            return

        tracked_user_list = []
        for track in tracking_list:
            user = await User.get(self.bot.db_session, track.user_id)
            tracked_user_list.append(
                f"• [{user.username}](https://osu.ppy.sh/users/{user.user_id})"
            )

        user_list = "\n".join(tracked_user_list)
        await interaction.followup.send(
            f"🔍 **({len(tracking_list)})** Users being tracked in this channel:\n{user_list}",
            suppress_embeds=True,
        )

    @command_group.command(name="ls_add", description="See your latest osu! score.")
    @app_commands.describe(user="Your osu! username or User ID.")
    async def ls_add(self, interaction: discord.Interaction, user: str):
        """See your latest osu! score."""
        await interaction.response.defer()

        osu_db_user = await User.get(self.bot.db_session, user)
        if not osu_db_user:
            await interaction.followup.send(
                f"❌ osu! user '{user}' has not been found."
            )
            return

        discord_db_user = await DiscordUsers.get(self.bot.db_session, interaction)
        if not discord_db_user:
            discord_db_user = await DiscordUsers.add(
                self.bot.db_session, osu_db_user, interaction
            )
            await interaction.followup.send(
                f"✅ osu! user '{osu_db_user.username}' has been added to your Discord account."
            )
        else:
            await DiscordUsers.update(self.bot.db_session, osu_db_user, interaction)
            await interaction.followup.send(
                f"✅ osu! user '{osu_db_user.username}' has been updated to your Discord account."
            )

    # Helper method to handle missing interaction data
    async def _ensure_interaction_context(
        self, interaction: discord.Interaction
    ) -> bool:
        if not interaction.channel or not interaction.guild:
            await interaction.response.send_message(
                "❌ This command must be used in a server channel.", ephemeral=True
            )
            return False
        return True


async def setup(bot: commands.Bot):
    osu_group = OsuGroup(bot)
    await bot.add_cog(osu_group)
