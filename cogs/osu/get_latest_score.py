from discord.ext import commands
from psycopg2.extras import wait_select
import psycopg2
import os
from .recent_scores import Api_call
from .embed import Calculators

aconn = psycopg2.connect(f'dbname={os.getenv("db")} user={os.getenv("login")} password={os.getenv("passw")}', async=1)
wait_select(aconn)
ac = aconn.cursor()


class LatestScore:
    def __init__(self, bot):
        self.bot = bot

    async def get_info(self, ctx):
        ac.execute("SELECT username, user_id, pp_rank "
                   "FROM latest_score WHERE discord_user_id = %s", (ctx.author.id,))
        wait_select(ac.connection)
        return ac.fetchone()

    async def check_info(self, ctx):
        info = await self.get_info(ctx)
        if not info:
            await ctx.send("Please add your osu! nickname via 'lsn' command.")
        else:
            await self.embed(ctx, info)

    async def check_if_exists_in_osu(self, username):
        return await Api_call.get_user(username)

    async def get_score(self, user_id, limit):
        return await Api_call.get_user_recent(user_id, limit)

    async def get_beatmaps(self, beatmap_id):
        return await Api_call.get_beatmaps(beatmap_id)

    async def count_recent_objects(self, recent_score):
        return recent_score.count300 + recent_score.count100 + recent_score.count50 \
               + recent_score.countmiss

    async def beatmap_objects(self, beatmap):
        bmap = await Calculators.parse_beatmap_file(beatmap.beatmap_id)
        return len(bmap.hitobjects)

    async def calculate_map_percentage_done(self, beatmap, recent_score):
        try:
            return (round((await self.count_recent_objects(recent_score)
                           / await self.beatmap_objects(beatmap)) * 100, 2)) \
                if str(recent_score.rank) == "F" else 100
        except ZeroDivisionError:
            return 0

    async def format_map_percatange_done(self, beatmap, recent_score):
        percentage = str(await self.calculate_map_percentage_done(beatmap, recent_score))
        return f"Completion: **{percentage}%**"

    async def check_if_exists_in_tracked(self, player):
        ac.execute("SELECT username, user_id, pp_rank "
                   "FROM track "
                   "WHERE username ILIKE %s", (player, ))
        wait_select(ac.connection)
        return ac.fetchone()

    async def custom_ls(self, ctx, player, limit=1):
        get_user = await self.check_if_exists_in_osu(player)
        if get_user:
            user_stuff = get_user.username, get_user.user_id, get_user.pp_rank
            await self.embed(ctx, user_stuff, limit)
        else:
            await ctx.send(f"Couldn't find a player named '{player}'.")

    async def check_if_exists(self, ctx):
        ac.execute("SELECT discord_user_id "
                   "FROM latest_score "
                   "WHERE discord_user_id = %s", (ctx.author.id, ))
        wait_select(ac.connection)
        return ac.fetchone()

    # if new nickname
    async def add_nickname(self, ctx, nickname):
        get_user = await self.check_if_exists_in_osu(nickname)
        check = await self.check_if_exists(ctx)
        if get_user and not check:
            ac.execute("INSERT INTO "
                       "latest_score (username, user_id, pp_rank, discord_user_id) "
                       "VALUES (%s, %s, %s, %s)",
                       (get_user.username, get_user.user_id, get_user.pp_rank, ctx.author.id))
            wait_select(ac.connection)
            return True
        elif get_user and check:
            await self.change_nickname(ctx, get_user)
            return True
        else:
            return

    # if nickname exists, update/change into a new one
    async def change_nickname(self, ctx, get_user):
        ac.execute("UPDATE latest_score "
                   "SET username = %s, user_id = %s, pp_rank = %s "
                   "WHERE discord_user_id = %s", (get_user.username, get_user.user_id,
                                                  get_user.pp_rank, ctx.author.id))
        wait_select(ac.connection)

    async def embed(self, ctx, user_stuff, limit=1):
        username, user_id, pp_rank = user_stuff
        recent_score = await self.get_score(user_id, limit)
        if recent_score:
            beatmapset = await self.get_beatmaps(recent_score.beatmap_id)
            ls = await self.format_map_percatange_done(beatmapset, recent_score)
            await self.bot.get_cog("EmbedMessage").prepare_message\
                (user_stuff, {"score": recent_score, "beatmap": beatmapset}, [ctx.channel.id], ls)
        else:
            await ctx.send(f"{username} has no latest scores.")


def setup(bot):
    bot.add_cog(LatestScore(bot))
