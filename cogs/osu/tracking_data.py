import psycopg2
from psycopg2.extras import wait_select
import os

aconn = psycopg2.connect(f'dbname={os.getenv("db")} user={os.getenv("login")} password={os.getenv("passw")}', async=1)
wait_select(aconn)

"""
    This is used for formatting the actual data for tracking, for ex.:
    If there is a player with the same name that is being tracked on
    different guilds, the class will parse and format the data into
    a readable dictionary, so the background task wouldn't need to make 
    unnecessary api calls and waste resources on doing the same thing
    more than 1 time.
    
    Returns
    -------
    dict(self.player_list)
        A dictionary with the needed data for tracking
"""


class Data:
    def __init__(self):
        self.player_list = {}

    async def distinct_user_id_list(self):
        ac = aconn.cursor()
        ac.execute("SELECT username, user_id, pp_rank, channel_id "
                   "FROM track WHERE user_id IN "
                   "(SELECT user_id FROM track GROUP BY user_id HAVING "
                   "(SELECT COUNT(user_id)) = 1)")
        wait_select(ac.connection)
        return ac.fetchall()

    async def multiple_user_id_list(self):
        ac = aconn.cursor()
        ac.execute("SELECT username, user_id, pp_rank, channel_id "
                   "FROM track WHERE user_id IN "
                   "(SELECT user_id FROM track GROUP BY user_id HAVING "
                   "(SELECT COUNT(user_id)) > 1)")
        wait_select(ac.connection)
        return ac.fetchall()

    async def list_for_multiple_format(self, multiple_list):
        formatted_dict = {}
        for username, user_id, pp_rank, channel_id in multiple_list:
                if (username, user_id, pp_rank) not in formatted_dict.keys()\
                        and [channel_id] not in formatted_dict.values():
                    formatted_dict[(username, user_id, pp_rank)] = [channel_id]
                else:
                    formatted_dict[(username, user_id, pp_rank)].append(channel_id)
        return formatted_dict

    async def list_for_distinct_format(self, distinct_list):
        formatted_dict = {}
        for username, user_id, pp_rank, channel_id in distinct_list:
            formatted_dict[(username, user_id, pp_rank)] = [channel_id]
        return formatted_dict

    async def full_list_format(self, multi_list, distinct_list):
        return {**multi_list, **distinct_list}

    # should always be called on almost any database update
    async def update_list(self):
        multi = await self.list_for_multiple_format(await self.multiple_user_id_list())
        distinct = await self.list_for_distinct_format(await self.distinct_user_id_list())
        self.player_list = await self.full_list_format(multi, distinct)
        await self.placeholder_list()

    async def placeholder_list(self):
        if not self.player_list:
            self.player_list['Fuuka', 5120516, 100000] = [456030887159529504]


TrackingData = Data()
