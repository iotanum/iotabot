from .api_calls import Api

Api_call = Api()
dup = dict()


class SubmittedScore:
    async def duplicate_score(self, date, user_id, channel_id):
        for channel in channel_id:
            if (channel, user_id) in dup.keys():
                if dup[(channel, user_id)] == date:
                    return
                del dup[(channel, user_id)]
                dup[(channel, user_id)] = date
                return True
            dup[(channel, user_id)] = date
            return True

    async def failed_score(self, rank):
        return str(rank) == 'F'

    async def both_checks(self, score, user_id, channel_id):
        if not await self.failed_score(score.rank) and await self.duplicate_score(score.date, user_id, channel_id):
            return True

    async def recent_score(self, user_id, channel_id):
        score = await Api_call.get_user_recent(user_id)
        if score and await self.both_checks(score, user_id, channel_id):
            return {"score": score, "beatmap": await Api_call.get_beatmaps(score.beatmap_id)}


CheckForScores = SubmittedScore()
