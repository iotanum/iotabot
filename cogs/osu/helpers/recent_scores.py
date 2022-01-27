from cogs.osu.helpers.api_calls import Api

dup = dict()


class SubmittedScore:
    def __init__(self):
        self.osu_api = Api()

    async def is_duplicate_score(self, date, user_id, channel_id):
        for channel in channel_id:
            if (channel, user_id) in dup.keys():
                if dup[(channel, user_id)] == date:
                    return
                del dup[(channel, user_id)]
                dup[(channel, user_id)] = date
                return True
            dup[(channel, user_id)] = date
            return True

    async def is_failed_score(self, rank):
        return str(rank) == 'F'

    async def is_valid_new_score(self, score, user_id, channel_id):
        if not await self.is_failed_score(score.rank):
            if await self.is_duplicate_score(score.date, user_id, channel_id):
                return True

    async def get_recent_score(self, user_id, channel_id):
        score = await self.osu_api.get_user_recent(user_id, limit=0)
        if score and await self.is_valid_new_score(score, user_id, channel_id):
            score.enabled_mods = score.enabled_mods.shortname
            return {"score": score, "beatmap": await self.osu_api.get_beatmaps(score.beatmap_id)}

