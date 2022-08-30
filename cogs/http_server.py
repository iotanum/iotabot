from discord.ext import commands
import discord

import aiohttp
from aiohttp import web

import os
import json


HTTP_SERVER_PORT = os.getenv("HTTP_SERVER_PORT")
GBF_BOT_SERVER_PORT = os.getenv("GBF_BOT_SERVER_PORT")


class HTTPServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.remote_ip = None
        self.verification_endpoint = '/verification'

    @commands.command()
    async def gbf(self, ctx, verification_code):
        if isinstance(ctx.channel, discord.channel.DMChannel):
            payload = {'verification_code': verification_code}

            async with aiohttp.ClientSession() as session:
                async with session.post(f'http://{self.remote_ip}:{GBF_BOT_SERVER_PORT}{self.verification_endpoint}',
                                        json=payload) as resp:
                    print(resp.status)
                    print(await resp.text())

    @commands.command()
    async def repeat(self, ctx, ip=None):
        if isinstance(ctx.channel, discord.channel.DMChannel):
            if self.remote_ip is None and ip is None:
                await ctx.send('Remote IP is missing! Please provide it via argument.')
            self.remote_ip = ip if ip is not None else self.remote_ip
            remote_ip = self.remote_ip if not None else ip
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://{remote_ip}:{GBF_BOT_SERVER_PORT}/repeat') as resp:
                    print(resp.status)
                    print(await resp.text())

    async def http_server(self):
        async def invoke_bot_command(request):
            r_body = await request.post()
            print(r_body)

            remote_ip = request.remote
            self.remote_ip = remote_ip

            discord_id = int(r_body['discord_id'])
            temp_img_name = r_body['image'].filename

            with open(temp_img_name, 'wb') as f:
                image = r_body['image'].file.read()
                f.write(image)
                f.close()

            image = discord.File(temp_img_name)

            user = await self.bot.fetch_user(discord_id)
            await user.send(content=temp_img_name, file=image)

            os.remove(temp_img_name)

        async def get_handler(request):
            return web.Response(text=f"{self.bot.user.name}")

        async def get_status(request):
            last_min_state = self.bot.get_cog('Status').api_minute_state
            resp = {"healthy": True if last_min_state > 0 else False}
            resp_status = 200 if last_min_state > 0 else 503

            return web.json_response(resp, status=resp_status)

        async def post_handler(request):
            await invoke_bot_command(request)
            return web.Response(status=200)

        app = web.Application()
        app.router.add_get("/verification", get_handler)
        app.router.add_post("/verification", post_handler)
        app.router.add_get("/status", get_status)

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, port=HTTP_SERVER_PORT)
        await self.bot.wait_until_ready()
        await site.start()
        print(f"HTTP server running on: {'0.0.0.0' if not site._host else site._host}:{site._port} ")


async def setup(bot):
    server = HTTPServer(bot)
    await bot.add_cog(server)
    bot.loop.create_task(server.http_server())
