from discord.ext import commands
import random
import asyncio


class Fun:
    counter = 0
    messages_until = 100

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def choose(self, ctx, *args):
        await ctx.send(random.choice(args))

    async def on_message(self, message):
        choices = ['...',
                   'LOL?',
                   "\U0001f612",
                   "\U0001f604",
                   f'{message.author.mention}',
                   'no u',
                   ';ddd']
        if message.author != self.bot.user:
            Fun.counter += 1
        if Fun.counter == Fun.messages_until:
            await asyncio.sleep(3)
            await self.bot.get_channel(message.channel.id).send(random.choice(choices))
            Fun.counter = 0
            Fun.messages_until = random.randint(1, 5000)


def setup(bot):
    bot.add_cog(Fun(bot))
