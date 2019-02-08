import psutil
import asyncio
from discord.ext import commands
from datetime import datetime
from .osu import api_calls, track_management

launch_time = datetime.utcnow()
api = api_calls.api


class Status:
    def __init__(self, bot):
        self.bot = bot
        self.api_minute_state = 0
        self.placeholder_state = 0
        self.bot.loop.create_task(self.last_minute_api())

    async def up_time(self):
        delta_uptime = datetime.utcnow() - launch_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        return days, hours, minutes, seconds

    async def total_minutes(self):
        days, hours, minutes, seconds = await self.up_time()
        if minutes == 0:
            minutes = 1
        return (days * 1444) + (hours * 60) + minutes

    async def track_status(self):
        return '✅' if self.bot.get_cog('Task').status else '❌'

    async def per_minute_api(self):
        per_minute_api = round(api.requests / await self.total_minutes(), 1)
        return f"{api.requests}, average of {per_minute_api}/min"

    async def last_minute_api(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            if self.api_minute_state == 0 and api.requests != 0:
                await self.bot.get_cog("Task").restart()
                print(f"Tracking has been restarted {datetime.utcnow()}")
            self.api_minute_state = api.requests - self.placeholder_state
            self.placeholder_state += self.api_minute_state
            await asyncio.sleep(60)

    @commands.cooldown(1, 1, commands.BucketType.guild)
    @commands.command(name='status', aliases=['s'])
    async def status(self, ctx):
        days, hours, minutes, seconds = await self.up_time()

        msg = await ctx.send(f'```coffeescript\n'
                             f'Tracking status - ' + str(await self.track_status()) + '\n'
                             + f'osu! API requests ->\ntotal - ' + await self.per_minute_api() + ",\n"
                             + f'last minute: {self.api_minute_state}\n'
                               f'Sleep time: ' + str(self.bot.get_cog("Task").list_sleep) + 's\n'
                               f'Per player sleep time: ' + str(self.bot.get_cog("Task").per_player_sleep) + 's```'
                             + f'```coffeescript\n'
                               f'CPU usage: {psutil.cpu_percent(interval=None)}%\n'
                               f'RAM usage: {psutil.virtual_memory().percent}%```'
                               f'```coffeescript\n'
                               f'# of servers: {str(len(self.bot.guilds))}\n'
                             + f'# of players: ' + str(await track_management.total_unique_tracking()) + '\n'
                             + f'Uptime: {days}d, {hours}h:{minutes}m:{seconds}s```')

        await self.fancy_reaction_stuff(msg, ctx)

    async def fancy_reaction_stuff(self, msg, ctx):
        await msg.add_reaction("\U0001f1f7")

        def check(reaction, user):
            return reaction.emoji == "\U0001f1f7"

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=10.0, check=check)
            await msg.add_reaction("\U0001f477")
        except asyncio.TimeoutError:
            pass
        else:
            await self.bot.get_cog("Task").restart(ctx)
            await msg.add_reaction("\U0001f44d")


def setup(bot):
    bot.add_cog(Status(bot))
