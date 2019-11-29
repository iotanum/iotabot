from discord.ext import commands
import asyncio
from .tracking_data import TrackingData as TD


class Debugging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.get_cog()

    def get_cog(self):
        self.tm = self.bot.get_cog('Tracking')
        self.task = self.bot.get_cog('Task')

    @commands.is_owner()
    @commands.group(hidden=True)
    async def debug(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid debug option passed.")

    @debug.command()
    async def list(self, ctx):
        user_list = ""
        for idx, username in enumerate(TD.tracked_players, 1):
            pi = TD.tracked_players[username]
            channels = list(channel for channel in pi['channels'])
            user_list += f"{idx}. {username}, tracking in: {channels}, online: {pi['online']}\n"
        await ctx.send(f"```{user_list}```")

    @debug.command()
    async def add(self, ctx, *, arg):
        usernames = arg.split(", ")
        await ctx.send(f"This will take about *{len(usernames) * 3 + 3}* seconds..")
        for username in usernames:
            get_user = await self.tm.osu_player_check(username)
            await self.tm.add_player(ctx.guild.id, ctx.channel.id, get_user)
            await asyncio.sleep(3)
        await ctx.send(f"Added {usernames}")

    @debug.command()
    async def starttrack(self, ctx):
        if not self.task.status:
            await self.task.start_task()
            await ctx.message.add_reaction("\U00002705")

    @debug.command()
    async def stoptrack(self, ctx):
        await self.task.stop_task()
        await ctx.message.add_reaction("\U00002705")

    @debug.group()
    async def sleep(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid sleep option passed.")

    @sleep.command()
    async def whole_list(self, ctx, seconds: int):
        self.task.list_sleep = seconds
        await ctx.message.add_reaction("\U00002705")

    @sleep.command()
    async def per_player(self, ctx, seconds: float):
        self.task.per_player_sleep = seconds
        await ctx.message.add_reaction("\U00002705")


def setup(bot):
    bot.add_cog(Debugging(bot))
