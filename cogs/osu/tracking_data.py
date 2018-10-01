import psycopg2
from psycopg2.extras import wait_select
import os

aconn = psycopg2.connect(f'dbname={os.getenv("db")} user={os.getenv("login")} password={os.getenv("passw")}', async=1)
wait_select(aconn)
ac = aconn.cursor()

"""
    This is used for formatting the actual data for tracking, for ex.:
    If there is a player with the same name that is being tracked on
    different guilds, the class will parse and format the data into
    a readable dictionary, so the background task wouldn't need to make 
    unnecessary api calls and waste resources on doing the same thing
    more than 1 time.

    Returns
    -------
    dict(self.tracked_players)
        A nested formatted dictionary with the needed data for tracking
        {'online': bool, 'user_id': user_id,
         'pp_rank': pp_rank, 'channels': list(channel_id)}}
"""


class Data:
    def __init__(self):
        self.tracked_players = {}

    async def get_whole_list(self):
        ac.execute("SELECT username, user_id, pp_rank, channel_id "
                   "FROM track")
        wait_select(ac.connection)
        return ac.fetchall()

    async def list_formatting(self, whole_list):
        formatted_dict = {}
        for username, user_id, pp_rank, channel_id in whole_list:
            if username not in formatted_dict.keys():
                formatted_dict[username] = {'online': bool(True), 'user_id': user_id,
                                            'pp_rank': pp_rank, 'channels': [channel_id]}
            else:
                formatted_dict[username]['channels'].append(channel_id)
        return formatted_dict

    # should always be called on almost any database update
    async def update_list(self):
        self.tracked_players = await self.list_formatting(await self.get_whole_list())
        await self.placeholder_list()

    async def placeholder_list(self):
        if not self.tracked_players:
            self.tracked_players['Fuuka'] = {'online': bool(False), 'user_id': 5120516,
                                             'pp_rank': 100000, 'channels': [456030887159529504]}


TrackingData = Data()
