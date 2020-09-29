from psycopg2.extras import wait_select

from .api_calls import Api
from .database_management import Database


class AfterSubmitChanges:
    def __init__(self, bot):
        self.bot = bot
        self.database = Database(self.bot)
        self.osu_api = Api()
        self.new_stuff = ""

    async def get_current_player_info(self, user_id):
        self.bot.db.execute("SELECT pp_raw, accuracy, pp_rank, pp_country_rank FROM track WHERE user_id = %s", (user_id, ))
        wait_select(self.bot.db.connection)
        c_pp, c_acc, c_rank, c_c_rank = self.bot.db.fetchone()
        return float(c_pp), float(c_acc), int(c_rank), int(c_c_rank)

    async def after_submit_data(self, user_id):
        get_user = await self.osu_api.get_user(int(user_id))
        pp = get_user.pp_raw
        accuracy = round(get_user.accuracy, 2)
        pp_rank = get_user.pp_rank
        country_rank = get_user.pp_country_rank
        return pp, accuracy, pp_rank, country_rank

    async def format_data(self, user_id):
        return {"current": await self.get_current_player_info(user_id), "new": await self.after_submit_data(user_id)}

    async def calc_changes(self, user_id):
        self.new_stuff = ""
        data = await self.format_data(user_id)
        c_pp, c_acc, c_rank, c_c_rank = data['current']
        pp, acc, rank, country_rank = data['new']
        calc_data = [round(pp - c_pp, 2), round(acc - c_acc, 2), rank - c_rank, country_rank - c_c_rank]
        await self.eval_changes(user_id, calc_data, data['new'])

    async def eval_changes(self, user_id, calc_data, new_data):
        changes = list()
        for var in calc_data:
            if var != 0.0 or var != 0:
                changes.append(var)
            else:
                changes.append(None)
        if all(var is None for var in changes):
            self.new_stuff = None
        else:
            await self.update_if_anything_changed(user_id, new_data)
            await self.text_format_if_changed(changes)

    async def update_if_anything_changed(self, user_id, new_data):
        pp, acc, rank, c_rank = new_data
        self.bot.db.execute("UPDATE track SET pp_raw = %s, accuracy = %s, pp_rank = %s, pp_country_rank = %s"
                            " WHERE user_id = %s", (pp, acc, rank, c_rank, user_id))
        wait_select(self.bot.db.connection)
        await self.database.update_list()

    async def text_format_if_changed(self, changes):
        for idx, var in enumerate(changes):
            if not var:
                continue
            elif var >= 1:
                self.new_stuff += f"+{var}" + await self.counter_magic(idx) + "\n"
            elif var <= 0:
                self.new_stuff += f"{var}" + await self.counter_magic(idx) + "\n"
        self.new_stuff = self.new_stuff[:-1]

    async def counter_magic(self, idx):
        choices = ["pp", "%", " ranks", " country ranks"]
        return choices[idx]

