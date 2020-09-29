from psycopg2.extras import wait_select

from .new_top_score import NewTopPlay
from .api_calls import Api


class Database:
    def __init__(self, bot):
        self.bot = bot
        self.top_scores = NewTopPlay(bot)
        self.osu_api = Api()
        self.players = {}

    async def add_player(self, guild_id, channel_id, get_user):
        self.bot.db.execute("INSERT INTO track "
                            "(guild_id, channel_id, user_id, username, pp_raw, accuracy, pp_rank, pp_country_rank, country) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (guild_id, channel_id, get_user.user_id, get_user.username, get_user.pp_raw,
                             round(get_user.accuracy, 2), get_user.pp_rank, get_user.pp_country_rank, get_user.country))
        wait_select(self.bot.db.connection)

        await self.top_scores.add_scores(get_user.username, get_user.user_id)
        await self.update_list()

    async def delete_user(self, ctx, username):
        self.bot.db.execute("DELETE FROM track where guild_id = %s and username ILIKE %s", (ctx.guild.id, username))
        wait_select(self.bot.db.connection)

        await self.top_scores.remove_scores(username)
        await self.update_list()

        return username

    # returns everything player related
    async def search_player(self, ctx, username):
        self.bot.db.execute("SELECT * FROM track WHERE guild_id = %s AND username ILIKE %s", (ctx.guild.id, username))
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchone()

    # returns channel_id
    async def search_channel(self, ctx):
        self.bot.db.execute("SELECT channel_id FROM track WHERE channel_id = %s", (ctx.channel.id,))
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchone()

    # returns guild_id, channel_id
    async def search_guild(self, ctx):
        self.bot.db.execute("SELECT guild_id, channel_id FROM track WHERE guild_id = %s", (ctx.guild.id,))
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchone()

    async def tracked_players_list(self, guild_id):
        self.bot.db.execute("SELECT username, user_id FROM track WHERE guild_id = %s ORDER BY pp_raw DESC", (guild_id,))
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchall()

    async def get_whole_player_list(self):
        self.bot.db.execute("SELECT username, user_id, pp_rank, channel_id "
                            "FROM track")
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchall()

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
        return await self.osu_api.get_user(username)

    async def osu_player_check(self, username):
        player = await self.osu_player_search(username)
        return player if player else None

    async def format_player_list(self, player_list):
        formatted_dict = {}
        for username, user_id, pp_rank, channel_id in player_list:
            if username not in formatted_dict.keys():
                formatted_dict[username] = {'online': bool(True), 'user_id': user_id,
                                            'pp_rank': pp_rank, 'channels': [channel_id]}
            else:
                formatted_dict[username]['channels'].append(channel_id)
        return formatted_dict

    # should always be called on almost any database update
    async def update_list(self):
        self.players = await self.format_player_list(await self.get_whole_player_list())
        if not self.players:
            await self.placeholder_list()

    async def placeholder_list(self):
        self.players['Fuuka'] = {'online': bool(False), 'user_id': 5120516,
                                 'pp_rank': 100000, 'channels': [456030887159529504]}

    async def total_unique_tracking(self):
        self.bot.db.execute("SELECT COUNT (DISTINCT username) FROM track")
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchone()[0]

