import asyncio
from discord.ext import commands
from .track_management import TrackingData
from .api_calls import api
from .recent_scores import CheckForScores


class Task:
    status = True

    def __init__(self, bot):
        self.bot = bot
        self.bg_sleep = 2
        self.bg_task = self.bot.loop.create_task(self.background_task())

    async def background_task(self):
        await self.bot.wait_until_ready()
        await TrackingData.update_list()
        while not self.bot.is_closed():
            for user, channels in TrackingData.player_list.items():
                username, user_id, pp_rank = user
                recent_data = await CheckForScores.recent_score(int(user_id), channels)
                if recent_data:
                    await self.bot.get_cog("EmbedMessage").prepare_message(user, recent_data, channels)
                    print(f"New score: {username}, Posted in: "
                          f"{list(self.bot.get_channel(int(channel_id)).guild.name for channel_id in channels)}")
                await asyncio.sleep(self.bg_sleep)

    async def restart(self, ctx):
        await asyncio.sleep(2)
        self.bg_task.cancel()
        await api.reset_api_calls()
        await asyncio.sleep(3)
        self.bg_task = self.bot.loop.create_task(self.background_task())
        Task.status = True
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
    @commands.command(hiddden=True)
    async def sleep(self, ctx, seconds: int):
        self.bg_sleep = seconds
        await ctx.message.add_reaction("\U00002705")


def setup(bot):
    bot.add_cog(Task(bot))
