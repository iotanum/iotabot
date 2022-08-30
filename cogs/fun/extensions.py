from discord.ext import commands


class FunExtensions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_fun_cogs(self):
        extensions = ['cogs.fun.random',
                      'cogs.fun.on_message_stuff',
                      'cogs.fun.edit_message'
                      ]

        for extension in extensions:
            try:
                await self.bot.load_extension(extension)

            except Exception as e:
                print(f'Failed to load extension "{extension}"')


async def setup(bot):
    fun_extensions = FunExtensions(bot)
    await fun_extensions.add_fun_cogs()
    await bot.add_cog(fun_extensions)
