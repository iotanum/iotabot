from discord.ext import commands
import discord


class TrackingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.get_cog("Task").database

    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.user)
    @commands.group(brief='Various osu! related commands/sub-commands', aliases=['os', 'o'])
    async def osu(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid osu option passed.")

    @osu.command(brief="Adds a player to the tracking list", aliases=['a'])
    async def add(self, ctx, *, arg):
        get_user = await self.database.osu_player_check(arg)
        server_checks = await self.database.server_checks(ctx)
        player_check = await self.database.player_check(ctx, arg)
        if get_user and not player_check:
            if not server_checks:
                await self.database.add_player(ctx.guild.id, ctx.channel.id, get_user)
            else:
                guild_id, channel_id = server_checks
                await self.database.add_player(guild_id, channel_id, get_user)
            await ctx.send(f"{get_user.username} has been successfully added.")
            print(f"New trackee: {get_user.username}, requested by: {ctx.author.name}, in: {ctx.guild.name}")
        elif not get_user:
            await ctx.message.add_reaction("\U0000274c")
        else:
            await ctx.send(f"{get_user.username} is already being tracked.")

    @osu.command(brief="Deletes a player from the tracking list", aliases=['del', 'd'])
    async def delete(self, ctx, *, arg):
        if await self.database.search_player(ctx, arg):
            await self.database.delete_user(ctx, arg)
            await ctx.message.add_reaction("\U00002705")
        else:
            await ctx.send(f"{arg} does not exist in the tracking list.")

    @osu.command(brief="Shows players user profile", aliases=['p'])
    async def profile(self, ctx, *, arg):
        embed = discord.Embed()
        embed.set_image(url=f"http://lemmmy.pw/osusig/sig.php?colour=pink&uname={arg}"
                            f"&pp=1&countryrank&flagshadow&flagstroke&darktriangles&onlineindicator="
                            f"undefined&xpbar")
        embed.set_footer(text="https://lemmmy.pw/osusig/")
        await ctx.send(embed=embed)

    @osu.command(brief="List of currently tracked players", aliases=['l'])
    async def list(self, ctx):
        check_list = await self.database.tracked_players_list(ctx.message.guild.id)
        if str(check_list) == "[]":
            await ctx.send("There's no players at this moment that are being tracked.\n"
                           "Please provide a channel with the 't' command that will be used for tracking.")
        else:
            embed = discord.Embed(title=f'{len(check_list)} players', color=0xFF0000,
                                  description=", ".join(f"[{str(username)}](https://osu.ppy.sh/u/{user_id})"
                                                        for username, user_id in check_list), inline=True)
            await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.user)
    @commands.group(brief="Shows your latest osu! score", aliases=['ls'], invoke_without_command=True,
                    name='latestscore')
    async def latest_score(self, ctx, player=None, limit=0):
        ls = self.bot.get_cog("LatestScore")
        if not player:
            await ls.check_info(ctx)
        else:
            db_user = await ls.check_if_exists_in_tracked(player)
            if db_user:
                await ls.embed(ctx, db_user, limit)
            else:
                await ls.custom_ls(ctx, player, limit)

    @latest_score.command(brief="Adds your nickname for 'ls'")
    async def set(self, ctx, *, arg):
        ls = self.bot.get_cog("LatestScore")
        if await ls.add_nickname(ctx, arg):
            await ctx.message.add_reaction("\U00002705")
        else:
            await ctx.send(f"{arg} does not exist.")

    @commands.command(brief="Get a list of recent scores of a player")
    async def lsl(self, ctx, username, limit=4):
        ls = self.bot.get_cog("LatestScore")
        user_stuff = await ls.get_list(username, limit)  # VAR referred to user object and their recent scores list
        if user_stuff:
            user, recents = user_stuff
            formatted_list = await ls.format_beatmap_string(recents)
            e = discord.Embed(title=f'Recent scores for {user.username}',
                              description="\n".join(f"__{idx}.__ {score}"
                                                    for idx, score in enumerate(formatted_list, 1)),
                              colour=0x36393E)
            await ctx.send(embed=e)
        elif user_stuff is False:
            await ctx.send(f"{username} has no recent scores.")


def setup(bot):
    bot.add_cog(TrackingCommands(bot))
