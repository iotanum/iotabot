from discord.ext import commands
import discord


class QuoteMessage:
    def __init__(self, bot):
        self.bot = bot

    async def get_message(self, channel, word_to_edit, limit):
        return await self.check_for_searchable(word_to_edit, await channel.history(limit=limit).flatten())

    async def check_for_searchable(self, word_to_edit, messages):
        for message in messages:
            if word_to_edit in message.content and await self.skip_command_msg(message) \
                    and await self.skip_bots_msg(message):
                return message

    async def skip_command_msg(self, message):
        return not message.content.startswith(await self.bot.get_prefix(message))

    async def skip_bots_msg(self, message):
        return message.author != self.bot.user

    async def edit_quote(self, msg_content, word_to_edit, edit_to):
        return msg_content.replace(word_to_edit, edit_to)

    async def check_limit(self, num):
        if num > 200 or num <= 0:
            return 20
        else:
            return num

    @commands.command(name='quote', aliases=['q'])
    async def edit_last_5_messages(self, ctx, word_to_edit, edit_to, limit=20):
        limit = await self.check_limit(limit)
        try:
            message = await self.get_message(ctx.channel, word_to_edit, limit)
            edited_msg_content = await self.edit_quote(message.content, word_to_edit, edit_to)
            e = discord.Embed(description=edited_msg_content, color=message.author.color)
            e.set_author(name=message.author.display_name, icon_url=message.author.avatar_url_as(format='png'))
            e.timestamp = message.created_at
            await ctx.send(embed=e)
        except AttributeError:
            pass


def setup(bot):
    bot.add_cog(QuoteMessage(bot))
