import asyncio
import logging

import discord
from discord.ext import commands

from app.models.tracking_channels import TrackingChannels
from cogs.osu import client as osu_client
from cogs.osu.shared_state import RequestCounter
from cogs.utils.score import is_new_score
from cogs.utils.score_embed import create_score_view


class ScoreTracker(commands.Cog):
    """
    Tracks scores for users and notifies channels of updates.
    """

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_session
        # osu! enforces 1200 requests/minute, but the API terms ask you to stay
        # under 60 and get in touch before going past it. One batch play count
        # lookup per cycle means a 2s floor keeps the idle loop at ~30/minute,
        # leaving the rest of the budget for actual score lookups.
        self.max_api_calls_per_minute = 60
        self.min_sleep_duration = 2
        self.max_sleep_duration = 5
        self.max_concurrent_lookups = 5
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_lookups)
        # Catch-up cap when a user's play count jumped by more than one
        # between cycles; keeps one user from dominating a cycle
        self.max_scores_per_check = 5
        self._warned_channels: set[int] = set()
        self._play_counts: dict[int, int] = {}

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
            channel = self.bot.get_channel(record.channel_id)
            if channel is None:
                # Deleted channel or one the bot can no longer see - a send to it
                # would take down the whole notification batch
                if record.channel_id not in self._warned_channels:
                    self._warned_channels.add(record.channel_id)
                    logging.warning(
                        f"Channel '{record.channel_id}' tracking user "
                        f"'{record.user_id}' not found; skipping it"
                    )
                continue
            tracking_map.setdefault(record.user_id, []).append(channel)
        return tracking_map

    async def get_played_users(self, user_ids: list[int]) -> dict[int, int | None]:
        """
        Batch-checks tracked users' play counts and returns the ones that
        played since the last check, mapped to the observed play count
        (None when the batch lookup failed and the user is checked blind).
        `play_count` moves on every submitted play (including fails), so an
        unchanged count means there is no new score to fetch for that user.
        `self._play_counts` is only advanced by `notify_new_scores` once the
        score check completed, so a failed check is retried next cycle.
        """
        played: dict[int, int | None] = {}
        # limit lookup to the max users batch size from osu api (default=50)
        for start in range(0, len(user_ids), osu_client.USERS_BATCH_SIZE):
            chunk = user_ids[start : start + osu_client.USERS_BATCH_SIZE]

            users = await osu_client.get_users(chunk)
            # Batch lookup failed, fall back to checking everyone in it
            if users is None:
                for user_id in chunk:
                    played[user_id] = None
                continue

            for user in users:
                stats = (
                    user.statistics_rulesets.osu if user.statistics_rulesets else None
                )
                if stats is None:
                    played[user.id] = None
                    continue

                last_count = self._play_counts.get(user.id)
                # != rather than >: play_count can also go down (stats
                # recalculations), and any movement means there was activity
                if last_count is None or stats.play_count != last_count:
                    played[user.id] = stats.play_count
        return played

    async def notify_new_scores(
        self, user_id: int, channels: list, observed_play_count: int | None
    ):
        """
        Checks for new scores for a user and sends notifications to the associated channels.
        """
        # A burst of plays moves the count by more than one - fetch enough
        # to cover the gap. max(1, ...) also covers play_count decreases
        last_count = self._play_counts.get(user_id)
        if observed_play_count is None or last_count is None:
            fetch_limit = 1
        else:
            fetch_limit = max(
                1, min(observed_play_count - last_count, self.max_scores_per_check)
            )

        async with self.request_semaphore:
            check_completed, scores = await is_new_score(
                self.db, user_id, limit=fetch_limit
            )
            # Commit the play count only once the check actually ran - after
            # a failed fetch (or a cancelled task) the old count stays put,
            # so the user is re-checked next cycle instead of losing the play
            if check_completed and observed_play_count is not None:
                self._play_counts[user_id] = observed_play_count
            if not scores:
                return
            views = [await create_score_view(self.db, score) for score in scores]

        for channel in channels:
            for view in views:
                try:
                    await channel.send(view=view)
                except discord.HTTPException:
                    # Missing permissions or the like, don't let one channel stop
                    # the score from reaching the remaining ones
                    logging.exception(f"Failed to send score embed to '{channel.id}'")
            await asyncio.sleep(0.1)  # Avoid hitting rate limits.

    async def calculate_sleep_time(self):
        """
        Calculates the appropriate sleep duration to respect API rate limits.
        """
        calls_made = RequestCounter.requests_per_last_minute()
        time_elapsed = RequestCounter.seconds_elapsed_in_window()
        rate_per_second = calls_made / time_elapsed
        max_rate = self.max_api_calls_per_minute / 60
        overshoot = (rate_per_second - max_rate) * 1.5  # Scale it up a bit to be safe.

        sleep_time = self.min_sleep_duration + max(overshoot, 0)
        return min(sleep_time, self.max_sleep_duration)

    async def run_tracking_loop(self):
        """
        Main background task that checks for new scores and respects API rate limits.
        """
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                tracking_map = await self.get_tracking_channels()
                played_users = await self.get_played_users(list(tracking_map))

                async with asyncio.TaskGroup() as tg:
                    for user_id, observed_count in played_users.items():
                        tg.create_task(
                            self.notify_new_scores(
                                user_id, tracking_map[user_id], observed_count
                            )
                        )
                sleep_time = await self.calculate_sleep_time()
                await asyncio.sleep(sleep_time)
            except Exception:
                logging.exception("Error in tracking loop")
                # Back off instead of retrying immediately, a failure that sticks
                # around would otherwise spin the loop with no delay at all
                await asyncio.sleep(self.max_sleep_duration)


async def setup(bot):
    await bot.add_cog(ScoreTracker(bot))
