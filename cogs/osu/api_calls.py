import aiohttp
import os
from osuapi import OsuApi, AHConnector

osu_api = OsuApi(os.getenv("osu_token"), connector=AHConnector())


class Api:
    requests = 0

    @staticmethod
    async def get_user(username):
        try:
            get_user = await osu_api.get_user(username)
            Api.requests += 1
            return get_user[0]

        except IndexError:
            return

    @staticmethod
    async def get_user_recent(user_id, limit=0, lslist=False):
        try:
            get_user_recent = await osu_api.get_user_recent(user_id, limit=limit + 1)
            Api.requests += 1
            return get_user_recent[limit if lslist is False else None]

        except IndexError:
            return

        except TypeError:
            return get_user_recent

    @staticmethod
    async def get_beatmaps(beatmap_id):
        try:
            get_beatmaps = await osu_api.get_beatmaps(beatmap_id=beatmap_id)
            Api.requests += 1
            return get_beatmaps[0]

        except IndexError:
            return

    @staticmethod
    async def get_user_best(user_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://osu.ppy.sh/api/get_user_best?"
                                   f"k={os.getenv('osu_token')}&"
                                   f"u={user_id}") as source:
                Api.requests += 1
                return await source.json()

    async def reset_api_calls(self):
        Api.requests = 0


api = Api()
