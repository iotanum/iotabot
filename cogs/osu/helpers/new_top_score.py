from psycopg2.extras import wait_select

from .api_calls import Api


class NewTopPlay:
    def __init__(self, bot):
        self.bot = bot
        self.osu_api = Api()
        self.new_score_num = int()

    #  aiohttp json returns a dictionary with it's individual key values as a list
    #  I only need beatmap_id, which is the 2nd element in the list, thus the 'magic number'
    async def format_user_best(self, top_scores):
        formatted = []
        for scores in top_scores:
            for info in scores.items():
                formatted.append(info[1])
                break
        return formatted

    async def add_player_scores(self, username, user_id, top_scores):
        self.bot.db.execute("INSERT INTO top_scores (username, user_id, scores) "
                            "SELECT * FROM (SELECT %s, %s, %s) "
                            "AS tmp "
                            "WHERE NOT EXISTS "
                            "(SELECT username FROM top_scores WHERE user_id = %s) "
                            "LIMIT 1;",
                            (username, user_id, top_scores, user_id))
        wait_select(self.bot.db.connection)

    async def add_scores(self, username, user_id):
        top_scores = await self.format_user_best(await self.osu_api.get_user_best(user_id))
        await self.add_player_scores(username, user_id, top_scores)

    async def remove_scores(self, username):
        self.bot.db.execute("DELETE FROM top_scores "
                            "WHERE username ILIKE %s",
                            (username, ))
        wait_select(self.bot.db.connection)

    async def get_top_scores(self, user_id):
        self.bot.db.execute("SELECT scores "
                            "FROM top_scores "
                            "WHERE user_id = %s",
                            (user_id, ))
        wait_select(self.bot.db.connection)
        return self.bot.db.fetchone()[0]  # psycopg2 always returns a list

    async def change_type(self, score_list):
        return score_list[1:][:-1].split(',')

    async def check_for_new_play(self, user_id):
        old_plays = await self.change_type(await self.get_top_scores(user_id))
        new_plays = await self.format_user_best(await self.osu_api.get_user_best(user_id))
        if new_plays != old_plays:
            self.new_score_num = await self.check_num_of_new_play(user_id, old_plays, new_plays)

    async def check_num_of_new_play(self, user_id, score_list, api_score_list):
        for idx, score in enumerate(score_list):
            if score != api_score_list[0 + idx]:
                await self.update_changes(api_score_list, user_id)
                return idx + 1
        return

    async def update_changes(self, new_plays_list, user_id):
        self.bot.db.execute("UPDATE top_scores "
                            "SET scores = %s "
                            "WHERE user_id = %s",
                            (new_plays_list, user_id))
        wait_select(self.bot.db.connection)

