import discord
import aiohttp


class GetAvatar:
    async def image_bytes(self, avatar_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                avatar_bytes = await response.read()
        return avatar_bytes

    async def avatar_url(self, member):
        return member.avatar_url_as(size=256)

    async def create_image(self, member):
        avatar_url = await self.avatar_url(member)
        image_bytes = await self.image_bytes(avatar_url)
        file_name = f'avatar.{"gif" if "gif" in avatar_url else "png"}'
        return discord.File(filename=file_name, fp=image_bytes)
