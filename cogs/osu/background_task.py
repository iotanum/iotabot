from discord.ext import tasks, commands
import asyncio
import aiohttp
import discord
import osuapi

from .helpers.database_management import Database
from cogs.osu.helpers.recent_scores import SubmittedScore
from .helpers.api_calls import Api

import traceback


class Task(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.database = Database(self.bot)
        self.submitted_score = SubmittedScore()
        self.osu_api = Api()
        self.embed_msg_cog = self.bot.get_cog("EmbedMessage")

        self.timer = {}
        self.per_player_sleep = 0.6

        self.background_task.start()

    async def format_player_info(self, player, submitted_play):
        player_information = self.database.players[player]

        return [player, player_information['user_id'], player_information['pp_rank']],\
                submitted_play, player_information['channels']

    async def log_submitted_scores_to_terminal(self, player_info):
        print(f"New score: {player_info['user_id']}, Posted in: "
              f"{list(self.bot.get_channel(channel_id).guild.name for channel_id in player_info['channels'])}")

    async def log_fatal_error_to_creator_dm(self):
        creator_discord_id = 450567441437687818
        try:
            await self.bot.get_user(creator_discord_id).send(f"```{traceback.format_exc()}```\n")
        except (discord.errors.HTTPException, AttributeError):
            error = str(traceback.format_exc())
            print(error)

            char_limit = 1999
            messages = [error[i:i+char_limit] for i in range(0, len(error), char_limit)]

            for message in messages:
                await self.bot.get_user(creator_discord_id).send(f"```{message}```\n")

    async def restart_tracking(self, ctx=None):
        self.background_task.restart()
        await self.osu_api.reset_api_calls()
        await self.bot.get_cog("Status").reset_api_calls()

        if ctx:
            print(f"Restarted the background task, requested by: {ctx.author}, from: {ctx.guild.name}")

    @tasks.loop(seconds=6, reconnect=True)
    async def background_task(self):
        try:
            for player in self.database.players:
                player_information = self.database.players[player]

                submitted_play = await self.submitted_score.get_recent_score(player_information['user_id'],
                                                                             player_information['channels'])
                if submitted_play:
                    submitted_play_info = await self.format_player_info(player, submitted_play)
                    await self.log_submitted_scores_to_terminal(player_information)
                    await self.embed_msg_cog.prepare_message(*submitted_play_info)

                    await asyncio.sleep(self.per_player_sleep)

        except (aiohttp.client_exceptions.ClientConnectionError, RuntimeError, asyncio.TimeoutError, osuapi.errors.HTTPError):
            pass

        except Exception as e:
            await self.log_fatal_error_to_creator_dm()

    @background_task.before_loop
    async def before_printer(self):
        print('waiting...')
        await self.database.update_list()
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Task(bot))
