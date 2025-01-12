import logging
import logging.handlers
from typing import List, Optional

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from app.core import DatabaseManager
from app.environment import APP_CONFIG


class Bot(commands.Bot):
    def __init__(
        self,
        *args,
        initial_extensions: List[str],
        db_session: callable,
        testing_guild_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.db_session = db_session
        self.testing_guild_id = testing_guild_id
        self.initial_extensions = initial_extensions
        self.start_time = None

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

    async def setup_hook(self) -> None:
        for extension in self.initial_extensions:
            await self.load_extension(extension)

        # In overriding setup hook,
        # we can do things that require a bot prior to starting to process events from the websocket.
        # In this case, we are using this to ensure that once we are connected, we sync for the testing guild.
        # You should not do this for every guild or for global sync, those should only be synced when changes happen.
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

        self.start_time = discord.utils.utcnow()
        task_cog = self.get_cog("ScoreTracker")
        self.loop.create_task(task_cog.run_tracking_loop())


async def on_tree_error(
    interaction: Interaction, error: app_commands.AppCommandError
) -> None:
    logging.error(f"Error processing command: {error}")


async def configure_logger():
    discord.utils.setup_logging(root=True)
    # Borderline disable ossapi logging, too spammy
    logging.getLogger("ossapi").setLevel(logging.WARNING)

    main_logger = logging.getLogger(__name__)
    main_logger.setLevel(logging.DEBUG)


async def run_bot():
    await configure_logger()

    exts = ["cogs.osu.commands", "cogs.task", "cogs.commands"]
    intents = discord.Intents.default()
    intents.message_content = True
    async with Bot(
        commands.when_mentioned,
        db_session=DatabaseManager.create_with_default_factory(),
        initial_extensions=exts,
        intents=intents,
        testing_guild_id=APP_CONFIG.get("TESTING_GUILD_ID"),
    ) as bot:
        bot.tree.on_error = on_tree_error
        await bot.start(APP_CONFIG.get("DISCORD_BOT_TOKEN"), reconnect=True)
