import os
import discord
import psycopg2
import asyncio
from psycopg2.extras import wait_select
from discord.ext import commands
from .api_calls import api
from .tracking_data import TrackingData
from .new_top_score import NewScore

aconn = psycopg2.connect(f'dbname={os.getenv("db")} user={os.getenv("login")} password={os.getenv("passw")}', async=1)
wait_select(aconn)
ac = aconn.cursor()


class OsuTracking:
    def __init__(self, bot):
        self.bot = bot

    async def add_player(self, guild_id, channel_id, get_user):
        ac.execute("INSERT INTO track "
                   "(guild_id, channel_id, user_id, username, pp_raw, accuracy, pp_rank, pp_country_rank, country) "
                   "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                   (guild_id, channel_id, get_user.user_id, get_user.username, get_user.pp_raw,
                    round(get_user.accuracy, 2), get_user.pp_rank, get_user.pp_country_rank, get_user.country))
        wait_select(ac.connection)
        await NewScore.add_scores(get_user.username, get_user.user_id)
        await TrackingData.update_list()

    async def delete_user(self, ctx, username):
        ac.execute("DELETE FROM track where guild_id = %s and username ILIKE %s", (ctx.guild.id, username))
        wait_select(ac.connection)
        await NewScore.remove_scores(username)
        await TrackingData.update_list()
        return username

    # returns everything player related
    async def search_player(self, ctx, username):
        ac.execute("SELECT * FROM track WHERE guild_id = %s AND username ILIKE %s", (ctx.guild.id, username))
        wait_select(ac.connection)
        return ac.fetchone()

    # returns channel_id
    async def search_channel(self, ctx):
        ac.execute("SELECT channel_id FROM track WHERE channel_id = %s", (ctx.channel.id,))
        wait_select(ac.connection)
        return ac.fetchone()

    # returns guild_id, channel_id
    async def search_guild(self, ctx):
        ac.execute("SELECT guild_id, channel_id FROM track WHERE guild_id = %s", (ctx.guild.id,))
        wait_select(ac.connection)
        return ac.fetchone()

    async def tracked_players_list(self, guild_id):
        ac.execute("SELECT username, user_id FROM track WHERE guild_id = %s ORDER BY pp_raw DESC", (guild_id,))
        wait_select(ac.connection)
        return ac.fetchall()

    # returns None if everything is ok,
    # returns True if guild exists, but channel doesn't
    async def server_checks(self, ctx):
        guild_check = await self.search_guild(ctx)
        channel_check = await self.search_channel(ctx)
        if guild_check:
            if channel_check:
                return
            else:
                return await self.wrong_channel(ctx, guild_check)
        elif not guild_check:
            await self.new_guild(ctx)

    async def wrong_channel(self, ctx, guild_info):
        guild_id, channel_id = guild_info
        await ctx.send(f"Next time use "
                       f"{self.bot.get_channel(channel_id).mention}"
                       f" for track-related commands.")
        return guild_id, channel_id

    async def new_guild(self, ctx):
        await ctx.send("This text channel will now be used for tracking.")
        print(f"New server: [{ctx.guild.name}, '{ctx.channel.name}']")

    # returns True if player is being tracked in given guild
    async def player_check(self, ctx, username):
        player_check = await self.search_player(ctx, username)
        if player_check:
            return True
        return

    async def osu_player_search(self, username):
        return await api.get_user(username)

    async def osu_player_check(self, username):
        player = await self.osu_player_search(username)
        return player if player else None

    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.guild)
    @commands.command(brief="Starts tracking a specific player", aliases=['t'])
    async def track(self, ctx, *, arg):
        get_user = await self.osu_player_check(arg)
        server_checks = await self.server_checks(ctx)
        player_check = await self.player_check(ctx, arg)
        if get_user and not player_check:
            if not server_checks:
                await self.add_player(ctx.guild.id, ctx.channel.id, get_user)
            else:
                guild_id, channel_id = server_checks
                await self.add_player(guild_id, channel_id, get_user)
            await ctx.send(f"{get_user.username} has been successfully added.")
            print(f"New trackee: {get_user.username}, requested by: {ctx.author.name}, in: {ctx.guild.name}")
        elif not get_user:
            await ctx.message.add_reaction("\U0000274c")
        else:
            await ctx.send(f"{get_user.username} is already being tracked.")

    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.guild)
    @commands.command(brief="Stops tracking a specific player", aliases=['d'])
    async def delete(self, ctx, *, arg):
        if await self.search_player(ctx, arg):
            await self.delete_user(ctx, arg)
            await ctx.message.add_reaction("\U00002705")
        else:
            await ctx.send(f"{arg} does not exist in the tracking list.")

    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.guild)
    @commands.command(brief="Shows players user profile", aliases=['p'], name="profile")
    async def user_profile(self, ctx, *, arg):
        embed = discord.Embed()
        embed.set_image(url=f"http://lemmmy.pw/osusig/sig.php?colour=pink&uname={arg}"
                            f"&pp=1&countryrank&flagshadow&flagstroke&darktriangles&onlineindicator="
                            f"undefined&xpbar")
        embed.set_footer(text="https://lemmmy.pw/osusig/")
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.guild)
    @commands.command(brief="List of currently tracked players", aliases=['c'])
    async def check(self, ctx):
        check_list = await self.tracked_players_list(ctx.message.guild.id)
        if str(check_list) == "[]":
            await ctx.send("There's no players at this moment that are being tracked.\n"
                           "Please provide a channel with the 't' command that will be used for tracking.")
        else:
            embed = discord.Embed(title=f'{len(check_list)} players', color=0xFF0000,
                                  description=", ".join(f"[{str(username)}](https://osu.ppy.sh/u/{user_id})"
                                                        for username, user_id in check_list), inline=True)
            await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def debug_track(self, ctx):
        user_list = ""
        for idx, (user, channel_id) in enumerate(TrackingData.player_list.items(), 1):
            username, user_id, pp_rank = user
            channels = list(channel for channel in channel_id)
            user_list += f"{idx}. {username}, {user_id}, tracking in: {channels}\n"
        await ctx.send(f"```{user_list}```")

    @commands.is_owner()
    @commands.command(hidden=True)
    async def cool_add(self, ctx, *, arg):
        usernames = arg.split(", ")
        await ctx.send(f"This will take about *{len(usernames) * 3 + 3}* seconds..")
        for username in usernames:
            get_user = await self.osu_player_check(username)
            await self.add_player(ctx.guild.id, ctx.channel.id, get_user)
            await asyncio.sleep(3)
        await ctx.send(f"Added {usernames}")


async def total_unique_tracking():
    ac.execute("SELECT COUNT (DISTINCT username) FROM track")
    wait_select(ac.connection)
    return ac.fetchone()[0]


def setup(bot):
    bot.add_cog(OsuTracking(bot))

