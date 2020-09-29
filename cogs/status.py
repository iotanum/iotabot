import psutil
import asyncio
from discord.ext import commands, tasks

from .osu.helpers.api_calls import Api
from .osu.helpers.database_management import Database

from datetime import datetime


launch_time = datetime.utcnow()


class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.osu_api = Api()
        self.database = Database(self.bot)
        self.api_minute_state = 0
        self.placeholder_state = 0
        self.tracking_start_time = datetime.utcnow()
        self.last_minute_api.start()

    async def up_time(self, track_up_time=False):
        delta_uptime = datetime.utcnow() - (launch_time if not track_up_time else self.tracking_start_time)
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        return days, hours, minutes, seconds

    async def total_minutes(self, track_up_time=False):
        tracking_up_time = await self.up_time(track_up_time=True)
        days, hours, minutes, seconds = await self.up_time() if not track_up_time else tracking_up_time
        if minutes == 0:
            minutes = 1
        return (days * 1444) + (hours * 60) + minutes

    async def track_status(self):
        return '✅' if self.bot.get_cog('Task').status else '❌'

    async def per_minute_api(self):
        per_minute_api = round(self.osu_api.requests / await self.total_minutes(track_up_time=True), 1)
        return f"{self.osu_api.requests}, average of {per_minute_api}/min"

    @tasks.loop(minutes=1)
    async def last_minute_api(self):
        await self.bot.wait_until_ready()
        # if self.api_minute_state == 0 and self.osu_api.requests != 0:
        #     await self.bot.get_cog("Task").restart()
        #     print(f"Tracking has been restarted {datetime.utcnow()}")
        self.api_minute_state = self.osu_api.requests - self.placeholder_state
        self.placeholder_state += self.api_minute_state

    @commands.cooldown(1, 1, commands.BucketType.guild)
    @commands.command(name='status', aliases=['s'])
    async def status(self, ctx):
        days, hours, minutes, seconds = await self.up_time()
        t_days, t_hours, t_minutes, t_seconds = await self.up_time(track_up_time=True)

        msg = await ctx.send(f'```coffeescript\n'
                             f'osu! API requests ->\ntotal - ' + await self.per_minute_api() + ",\n"
                             + f'last minute: {self.api_minute_state}\n'
                               f'Per player sleep time: ' + str(self.bot.get_cog("Task").per_player_sleep) + 's```'
                             + f'```coffeescript\n'
                               f'CPU usage: {psutil.cpu_percent(interval=None)}%\n'
                               f'RAM usage: {psutil.virtual_memory().percent}%```'
                               f'```coffeescript\n'
                               f'# of servers: {str(len(self.bot.guilds))}\n'
                             + f'# of players: ' + str(await self.database.total_unique_tracking()) + '\n'
                             + f'Uptime: {days}d, {hours}h:{minutes}m:{seconds}s\n'
                             + f'Tracking for: {t_days}d, {t_hours}h:{t_minutes}m:{t_seconds}s```')

        await self.fancy_reaction_stuff(msg, ctx)

    async def fancy_reaction_stuff(self, msg, ctx):
        await msg.add_reaction("\U0001f1f7")

        def check(reaction, user):
            return user == ctx.author and reaction.emoji == "\U0001f1f7"

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=10.0, check=check)
            await msg.add_reaction("\U0001f477")
        except asyncio.TimeoutError:
            pass
        else:
            await self.bot.get_cog("Task").restart_tracking(ctx)
            await msg.add_reaction("\U0001f44d")

    async def reset_api_calls(self):
        self.api_minute_state = 0
        self.placeholder_state = 0
        self.tracking_start_time = datetime.utcnow()


def setup(bot):
    bot.add_cog(Status(bot))
