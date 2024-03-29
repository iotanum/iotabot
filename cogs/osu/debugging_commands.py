from discord.ext import commands
from requests import get

from .helpers.database_management import Database

import asyncio


class Debugging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = Database(self.bot)
        self.tracked_players = self.database.players
        self.task = self.bot.get_cog('Task')

    @commands.is_owner()
    @commands.group(hidden=True)
    async def debug(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid debug option passed.")

    @debug.command()
    async def list(self, ctx):
        user_list = ""
        for idx, username in enumerate(self.tracked_players, 1):
            pi = self.tracked_players.tracked_players[username]
            channels = list(channel for channel in pi['channels'])
            user_list += f"{idx}. {username}, tracking in: {channels}, online: {pi['online']}\n"
        await ctx.send(f"```{user_list}```")

    @debug.command()
    async def add(self, ctx, *, arg):
        usernames = arg.split(", ")
        await ctx.send(f"This will take about *{len(usernames) * 3 + 3}* seconds..")
        for username in usernames:
            get_user = await self.database.osu_player_check(username)
            await self.database.add_player(ctx.guild.id, ctx.channel.id, get_user)
            await asyncio.sleep(3)
        await ctx.send(f"Added {usernames}")

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

    @commands.command(name='ip')
    async def give_ip(self, ctx):
        qonquest_id = 106747781552562176

        if ctx.message.author.id == qonquest_id or await self.bot.is_owner(ctx.message.author):
            ip = get('https://api.ipify.org').text
            await ctx.message.author.send(f"{ip}")


async def setup(bot):
    await bot.add_cog(Debugging(bot))
