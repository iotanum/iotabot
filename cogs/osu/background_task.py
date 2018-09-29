import asyncio
import aiohttp
from discord.ext import commands
from .track_management import TrackingData
from .api_calls import api
from .recent_scores import CheckForScores
import traceback

class Task:
    status = True

    def __init__(self, bot):
        self.bot = bot
        self.list_sleep = 2
        self.per_player_sleep = 0.5
        self.bg_task = self.bot.loop.create_task(self.background_task())

    async def background_task(self):
        await self.bot.wait_until_ready()
        await TrackingData.update_list()
        while not self.bot.is_closed():
            try:
                for user, channels in TrackingData.player_list.items():
                    username, user_id, pp_rank = user
                    recent_data = await CheckForScores.recent_score(int(user_id), channels)
                    if recent_data:
                        await self.bot.get_cog("EmbedMessage").prepare_message(user, recent_data, channels)
                        print(f"New score: {username}, Posted in: "
                              f"{list(self.bot.get_channel(int(channel_id)).guild.name for channel_id in channels)}")
                        await asyncio.sleep(self.per_player_sleep)
                await asyncio.sleep(self.list_sleep)
            except aiohttp.client_exceptions.ClientConnectionError:
                print("OSUAPI lib error skipped")
                continue
            except Exception as e:
                await self.bot.get_user(450567441437687818).send(f"```{traceback.format_exc()}```\n"
                                                                 f"Trying to reset the loop..")
                await self.restart()
                await self.bot.get_user(450567441437687818).send(f"Restarted\n```{asyncio.Task.all_tasks()}```")

    async def restart(self, ctx=None):
        await asyncio.sleep(2)
        self.bg_task.cancel()
        await api.reset_api_calls()
        await asyncio.sleep(3)
        self.bg_task = self.bot.loop.create_task(self.background_task())
        Task.status = True
        if ctx:
            print(f"Restarted the background task, requested by: {ctx.author}, from: {ctx.guild.name}")

    async def stop_task(self):
        self.bg_task.cancel()
        Task.status = False

    async def start_task(self):
        self.bg_task = self.bot.loop.create_task(self.background_task())
        Task.status = True

    @commands.is_owner()
    @commands.command(hidden=True)
    async def start_track(self, ctx):
        if not Task.status:
            await self.start_task()
            await ctx.message.add_reaction("\U00002705")

    @commands.is_owner()
    @commands.command(hidden=True)
    async def stop_track(self, ctx):
        await self.stop_task()
        await ctx.message.add_reaction("\U00002705")

    @commands.is_owner()
    @commands.group(hiddden=True)
    async def sleep(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid sleep option passed.")

    @commands.is_owner()
    @sleep.command(hidden=True)
    async def wlist(self, ctx, seconds: int):
        self.list_sleep = seconds
        await ctx.message.add_reaction("\U00002705")

    @commands.is_owner()
    @sleep.command(hidden=True)
    async def player(self, ctx, seconds: float):
        self.per_player_sleep = seconds
        await ctx.message.add_reaction("\U00002705")


def setup(bot):
    bot.add_cog(Task(bot))
