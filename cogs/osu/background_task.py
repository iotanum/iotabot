from discord.ext import commands
import asyncio
import aiohttp
from .tracking_data import TrackingData as TD
from .api_calls import api
from .recent_scores import CheckForScores
import traceback
from datetime import datetime


class Task(commands.Cog):
    status = True

    def __init__(self, bot):
        self.bot = bot
        self.timer = {}
        self.list_sleep = 6
        self.per_player_sleep = 0.6
        self.bg_task = self.bot.loop.create_task(self.background_task())

    async def background_task(self):
        await self.bot.wait_until_ready()
        await TD.update_list()
        embed = self.bot.get_cog("EmbedMessage")
        while not self.bot.is_closed():
            try:
                for username in TD.tracked_players:
                    pi = TD.tracked_players[username]  # pi will be referred as player information
                    if TD.tracked_players[username]['online'] is True:
                        submitted_play = await CheckForScores.recent_score(pi['user_id'], pi['channels'])
                        if submitted_play:
                            await embed.prepare_message([username, pi['user_id'], pi['pp_rank']],
                                                        submitted_play, pi['channels'])
                            print(f"New score: {username}, Posted in: "
                                f"{list(self.bot.get_channel(channel_id).guild.name for channel_id in pi['channels'])}")
                            await asyncio.sleep(self.per_player_sleep)
                await asyncio.sleep(self.list_sleep)

            except aiohttp.client_exceptions.ClientConnectionError:
                continue
            except (RuntimeError, asyncio.TimeoutError):
                continue
            except Exception as e:
                await self.bot.get_user(450567441437687818).send(f"```{traceback.format_exc()}```\n")

    async def on_member_update(self, member_before, member_after):
        try:
            await asyncio.sleep(10)
            if member_after.activity.name == 'osu!' and member_after.activity.assets['large_text'] != 'Guest':
                if member_after not in self.timer.keys():
                    username = member_after.activity.assets['large_text'].split(" ")[0]
                    if username in TD.tracked_players.keys():
                        self.timer[member_after] = datetime.utcnow(), username
                        TD.tracked_players[username]['online'] = True

        except Exception as e:
            if member_after in self.timer.keys():
                start_time, username = self.timer[member_after]
                del self.timer[member_after]
                TD.tracked_players[username]['online'] = False

    async def play_time(self, player_start_time):
        delta_uptime = datetime.utcnow() - player_start_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        return days, hours, minutes, seconds

    async def restart(self, ctx=None):
        await asyncio.sleep(2)
        self.bg_task.cancel()
        Task.status = False
        await api.reset_api_calls()
        await asyncio.sleep(2)
        self.bg_task = self.bot.loop.create_task(self.background_task())
        Task.status = True
        if ctx:
            print(f"Restarted the background task, requested by: {ctx.author}, from: {ctx.guild.name}")

    async def stop_task(self):
        self.bg_task.cancel()
        Task.status = False

    async def start_task(self):
        self.bg_task = self.bot.loop.create_task(self.background_task())
        Task.status = True


def setup(bot):
    bot.add_cog(Task(bot))
