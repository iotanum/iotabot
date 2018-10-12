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

    async def random_response_choices(self, message):
        return ['...',
                   'LOL?',
                   "\U0001f612",
                   "\U0001f604",
                   f'{message.author.mention}',
                   'no u',
                   ';ddd']

    async def on_message(self, message):
        if message.author != self.bot.user:
            Fun.counter += 1
        choices = await self.random_response_choices(message)
        if Fun.counter == Fun.messages_until:
            await asyncio.sleep(3)
            await self.bot.get_channel(message.channel.id).send(random.choice(choices))
            Fun.counter = 0
            Fun.messages_until = random.randint(1, 5000)

        await self.youtube(message)

    async def youtube(self, message):
        youtube_chars = ['youtu.be', 'youtube.com']
        timestamp_char = 't='
        if any(char in message.content for char in youtube_chars) and timestamp_char in message.content:
            await asyncio.sleep(0.5)
            await self.bot.get_channel(message.channel.id).send('\U0000261d timestamp btw')


def setup(bot):
    bot.add_cog(Fun(bot))
