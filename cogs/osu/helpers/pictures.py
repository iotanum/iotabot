class Pics:
    def __init__(self):
        self.user_avatar = ""
        self.user_link = ""
        self.beatmap_bg = ""
        self.beatmap_link = ""

    async def avatar(self, user_id):
        self.user_avatar = f"https://a.ppy.sh/{user_id}"

    async def link_user(self, user_id):
        self.user_link = f"https://osu.ppy.sh/u/{user_id}"

    async def beatmap_background(self, beatmapset_id):
        self.beatmap_bg = f"https://b.ppy.sh/thumb/{beatmapset_id}l.jpg"

    async def link_beatmap(self, beatmapset_id):
        self.beatmap_link = f"https://osu.ppy.sh/s/{beatmapset_id}"

    async def execute_all(self, user_id, beatmapset_id):
        await self.avatar(user_id)
        await self.link_user(user_id)
        await self.beatmap_background(beatmapset_id)
        await self.link_beatmap(beatmapset_id)

    async def get_pics(self, user_id, beatmapset_id):
        await self.execute_all(user_id, beatmapset_id)

