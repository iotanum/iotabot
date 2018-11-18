from discord.ext import commands
import discord


class QuoteMessage:
    def __init__(self, bot):
        self.bot = bot

    async def get_message(self, channel, word_to_edit):
        return await self.check_for_searchable(word_to_edit, await channel.history(limit=20).flatten())

    async def check_for_searchable(self, word_to_edit, messages):
        for message in messages:
            if word_to_edit in message.content and await self.skip_command_msg(message):
                return message

    async def skip_command_msg(self, message):
        return not message.content.startswith(await self.bot.get_prefix(message))

    async def edit_quote(self, msg_content, word_to_edit, edit_to):
        return msg_content.replace(word_to_edit, edit_to)

    @commands.command(name='quote', aliases=['q'])
    async def edit_last_5_messages(self, ctx, word_to_edit, edit_to):
        try:
            message = await self.get_message(ctx.channel, word_to_edit)
            edited_msg_content = await self.edit_quote(message.content, word_to_edit, edit_to)
            e = discord.Embed(description=edited_msg_content, color=ctx.author.color)
            e.set_author(name=message.author.display_name, icon_url=message.author.avatar_url_as(format='png'))
            e.timestamp = message.created_at
            await ctx.send(embed=e)
        except AttributeError:
            pass


def setup(bot):
    bot.add_cog(QuoteMessage(bot))
