import asyncio
import random


class OnMsg:
    counter = 0
    messages_until = 100

    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        await self.on_message_no_bot(message)
        await self.random_response(message)
        await self.yt_timestamp_notify(message)

    async def on_message_no_bot(self, message):
        if message.author != self.bot.user:
            OnMsg.counter += 1

    async def random_response(self, message):
        choices = await self.random_response_choices(message)
        if OnMsg.counter == OnMsg.messages_until:
            await asyncio.sleep(3)
            await self.bot.get_channel(message.channel.id).send(random.choice(choices))
            OnMsg.counter = 0
            OnMsg.messages_until = random.randint(1, 5000)

    async def random_response_choices(self, message):
        return ['...',
                'LOL?',
                "\U0001f612",
                "\U0001f604",
                f'{message.author.mention}',
                'no u',
                ';ddd']

    async def youtube_timestamp_check(self, message):
        youtube_chars = ['youtu.be', 'youtube.com']
        timestamp_char = 't='
        if any(char in message.content for char in youtube_chars) and timestamp_char in message.content:
            return True

    async def yt_timestamp_notify(self, message):
        if await self.youtube_timestamp_check(message):
            await asyncio.sleep(0.5)
            await self.bot.get_channel(message.channel.id).send('\U0000261d timestamp btw')


def setup(bot):
    bot.add_cog(OnMsg(bot))
