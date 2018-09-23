from discord.ext import commands
import random
import asyncio


class Fun:
    counter = 0
    messages_until = 100

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='500hp')
    async def hp500(self, ctx):
        await ctx.send("building the block and going nuts with 500+whp and 500tq is a LOT of car to handle. "
                       "A lot of people who've never owned or driven a powerful car don't realize just how "
                       "much power even 400whp is. Honestly if you NEED 450+whp for the street, you're going "
                       "to kill yourself or someone else sooner or later because if you live in a decent sized "
                       "city, you're just not going to be able to use the power for more than a single gear - "
                       "assuming your street tires can even hook the power to the ground")

    @commands.command()
    async def choose(self, ctx, *args):
        await ctx.send(random.choice(args))

    @commands.command()
    async def iota(self, ctx):
        await self.bot.get_user(137214686973132800).send("<:iota:492312478726750208>")

    async def on_message(self, message):
        choices = ['...',
                   'LOL?',
                   "\U0001f612",
                   "\U0001f604",
                   f'{message.author.mention}',
                   'no u']
        if message.author != self.bot.user:
            Fun.counter += 1
        if Fun.counter == Fun.messages_until:
            await asyncio.sleep(3)
            await self.bot.get_channel(message.channel.id).send(random.choice(choices))
            Fun.counter = 0
            Fun.messages_until = random.randint(1, 5000)


def setup(bot):
    bot.add_cog(Fun(bot))
