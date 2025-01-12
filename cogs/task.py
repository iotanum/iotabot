import asyncio
import logging

from discord.ext import commands

from app.models.tracking_channels import TrackingChannels
from cogs.osu.shared_state import RequestCounter
from cogs.utils.score import is_new_score
from cogs.utils.score_embed import create_score_embed


class ScoreTracker(commands.Cog):
    """
    Tracks scores for users and notifies channels of updates.
    """

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_session
        self.max_api_calls_per_minute = 500
        self.min_sleep_duration = 1
        self.max_sleep_duration = 5

    @commands.Cog.listener()
    async def on_ready(self):
        print("ScoreTracker is ready")

    async def get_tracking_channels(self):
        """
        Fetches the list of users and their corresponding tracking channels from the database.
        Returns a dictionary mapping user IDs to channel objects.
        """
        tracking_list = await TrackingChannels.get_all(self.db)
        tracking_map = dict()
        for record in tracking_list:
            tracking_map.setdefault(record.user_id, []).append(
                self.bot.get_channel(record.channel_id)
            )
        return tracking_map

    async def notify_new_scores(self, user_id: int, channels: list):
        """
        Checks for new scores for a user and sends notifications to the associated channels.
        """
        score = await is_new_score(self.db, user_id)
        if score:
            embed = await create_score_embed(self.db, score)
            for channel in channels:
                await channel.send(embed=embed)
                await asyncio.sleep(0.1)  # Avoid hitting rate limits.

    async def calculate_sleep_time(self):
        """
        Calculates the appropriate sleep duration to respect API rate limits.
        """
        calls_made = RequestCounter.requests_per_last_minute()
        time_elapsed = RequestCounter.seconds_elapsed_in_window()
        remaining_calls = self.max_api_calls_per_minute - calls_made
        rate_per_second = calls_made / time_elapsed
        max_rate = self.max_api_calls_per_minute / 60
        overshoot = (rate_per_second - max_rate) * 1.5  # Scale it up a bit to be safe.

        if overshoot > 0:
            sleep_time = min(
                self.max_sleep_duration, self.min_sleep_duration + overshoot
            )
        else:
            sleep_time = self.min_sleep_duration

        sleep_time = max(
            self.min_sleep_duration, min(sleep_time, self.max_sleep_duration)
        )
        logging.info(
            f"Sleeping - {sleep_time:.2f}s, remaining requests - {remaining_calls}, "
            f"next minute window in: {60 - time_elapsed:.2f}s"
        )
        return max(self.min_sleep_duration, min(sleep_time, self.max_sleep_duration))

    async def run_tracking_loop(self):
        """
        Main background task that checks for new scores and respects API rate limits.
        """
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            tracking_map = await self.get_tracking_channels()

            async with asyncio.TaskGroup() as tg:
                for user_id, channels in tracking_map.items():
                    tg.create_task(self.notify_new_scores(user_id, channels))
            sleep_time = await self.calculate_sleep_time()
            await asyncio.sleep(sleep_time)


async def setup(bot):
    await bot.add_cog(ScoreTracker(bot))
