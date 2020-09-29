from discord.ext import commands


class OsuExtensions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.add_osu_cogs()

    def add_osu_cogs(self):
        extensions = ['cogs.osu.embed',
                      'cogs.osu.background_task',
                      'cogs.osu.tracking_commands',
                      'cogs.osu.get_latest_score',
                      'cogs.osu.debugging_commands']

        for extension in extensions:
            try:
                self.bot.load_extension(extension)

            except Exception as e:
                print(f'Failed to load extension "{extension}", {e}')


def setup(bot):
    bot.add_cog(OsuExtensions(bot))
