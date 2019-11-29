import discord
from discord.ext import commands
import random
from .get_avatar import GetAvatar


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def choose(self, ctx, *args):
        await ctx.send(random.choice(args))

    @commands.command(name='avatar', brief='Gets discord user avatar')
    async def get_avatar(self, ctx, member: discord.Member = None):
        async with ctx.typing():
            avatar_file = await GetAvatar().create_image(member or ctx.author)
            await ctx.send(file=avatar_file)


def setup(bot):
    bot.add_cog(Fun(bot))
