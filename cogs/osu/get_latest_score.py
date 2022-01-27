from discord.ext import commands
from psycopg2.extras import wait_select

from .helpers.api_calls import Api
from .helpers.performance_points import PP

import asyncio


class LatestScore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.osu_api = Api()
        self.beatmap_calculator = PP()

    async def get_info(self, ctx):
        self.bot.db.execute("SELECT username, user_id, pp_rank "
                            "FROM latest_score WHERE discord_user_id = %s", (ctx.author.id,))
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchone()

    async def check_info(self, ctx):
        info = await self.get_info(ctx)
        if not info:
            await ctx.send("Please add your osu! nickname via 'lsn' command.")
        else:
            await self.embed(ctx, info)

    async def check_if_exists_in_osu(self, username):
        return await self.osu_api.get_user(username)

    async def get_score(self, user_id, limit, lslist=False):
        return await self.osu_api.get_user_recent(user_id, limit, lslist)

    async def get_beatmaps(self, beatmap_id):
        return await self.osu_api.get_beatmaps(beatmap_id)

    async def count_recent_objects(self, recent_score):
        return recent_score.count300 + recent_score.count100 + recent_score.count50 \
               + recent_score.countmiss

    async def beatmap_objects(self, beatmap):
        bmap = await self.beatmap_calculator.parse_beatmap_file(beatmap.beatmap_id)
        return len(bmap.hitobjects)

    async def calculate_map_percentage_done(self, beatmap, recent_score):
        try:
            return (round((await self.count_recent_objects(recent_score)
                           / beatmap.max_combo) * 100, 2)) \
                if str(recent_score.rank) == "F" else 100
        except ZeroDivisionError:
            return 0

    async def format_map_percatange_done(self, beatmap, recent_score):
        percentage = str(await self.calculate_map_percentage_done(beatmap, recent_score))
        return f"Completion: **{percentage}%**"

    async def check_if_exists_in_tracked(self, player):
        self.bot.db.execute("SELECT username, user_id, pp_rank "
                            "FROM track "
                            "WHERE username ILIKE %s", (player, ))
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchone()

    async def custom_ls(self, ctx, player, limit=0):
        get_user = await self.check_if_exists_in_osu(player)
        if get_user:
            user_stuff = get_user.username, get_user.user_id, get_user.pp_rank
            await self.embed(ctx, user_stuff, limit)
        else:
            await ctx.send(f"Couldn't find a player named '{player}'.")

    async def check_if_exists(self, ctx):
        self.bot.db.execute("SELECT discord_user_id "
                            "FROM latest_score "
                            "WHERE discord_user_id = %s", (ctx.author.id, ))
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchone()

    # if new nickname
    async def add_nickname(self, ctx, nickname):
        get_user = await self.check_if_exists_in_osu(nickname)
        check = await self.check_if_exists(ctx)
        if get_user and not check:
            self.bot.db.execute("INSERT INTO "
                                "latest_score (username, user_id, pp_rank, discord_user_id) "
                                "VALUES (%s, %s, %s, %s)",
                                (get_user.username, get_user.user_id, get_user.pp_rank, ctx.author.id))
            wait_select(self.bot.db.connection)
            return True
        elif get_user and check:
            await self.change_nickname(ctx, get_user)
            return True
        else:
            return

    async def get_list(self, player, limit):
        get_user = await self.check_if_exists_in_osu(player)
        if get_user:
            recents = await self.get_score(get_user.user_id, limit, lslist=True)
            if recents:
                return get_user, recents  # If everything is OK - return user and recent score objects
            else:
                return False  # Only want to handle if there are no recent scores, otherwise - ignore
        else:
            return

    async def format_beatmap_string(self, recents):
        scores = []
        for recent in recents:
            beatmap = await self.get_beatmaps(recent.beatmap_id)
            accuracy = await self.beatmap_calculator.submitted_accuracy_calc(recent)
            song_name = f"{beatmap.artist} - {beatmap.title} *[{beatmap.version}]*"
            if str(recent.enabled_mods) == "":
                recent.enabled_mods = "NoMod"
            mods_and_acc = f" **+ {recent.enabled_mods}** ({accuracy}%)\n"
            combo = f"**{recent.maxcombo}x**/({beatmap.max_combo}x) "
            score = "{ " + f"{recent.count300} / {recent.count100} / {recent.count50} / {recent.countmiss}" + " }"
            scores.append(song_name + "   " + mods_and_acc + combo + score)
            await asyncio.sleep(0.2)
        return scores

    # if nickname exists, update/change into a new one
    async def change_nickname(self, ctx, get_user):
        self.bot.db.execute("UPDATE latest_score "
                            "SET username = %s, user_id = %s, pp_rank = %s "
                            "WHERE discord_user_id = %s", (get_user.username, get_user.user_id,
                                                           get_user.pp_rank, ctx.author.id))
        wait_select(self.bot.db.connection)

    async def embed(self, ctx, user_stuff, limit=0):
        username, user_id, pp_rank = user_stuff
        recent_score = await self.get_score(user_id, limit)
        if recent_score:
            recent_score.enabled_mods = recent_score.enabled_mods.shortname
            beatmapset = await self.get_beatmaps(recent_score.beatmap_id)
            ls = await self.format_map_percatange_done(beatmapset, recent_score)
            await self.bot.get_cog("EmbedMessage").prepare_message\
                (user_stuff, {"score": recent_score, "beatmap": beatmapset}, [ctx.channel.id], ls)
        else:
            await ctx.send(f"{username} has no latest scores.")


def setup(bot):
    bot.add_cog(LatestScore(bot))
