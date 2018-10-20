class FunExtensions:
    def __init__(self, bot):
        self.bot = bot
        self.add_fun_cogs()

    def add_fun_cogs(self):
        extensions = ['cogs.fun.random',
                      'cogs.fun.on_message_stuff'
                      ]

        for extension in extensions:
            try:
                self.bot.load_extension(extension)

            except Exception as e:
                print(f'Failed to load extension "{extension}"')


def setup(bot):
    bot.add_cog(FunExtensions(bot))
