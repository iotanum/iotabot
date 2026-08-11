import asyncio
import logging
import time
from datetime import datetime, timezone

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
        # under 60 and get in touch before going past it.
        # The wait used to be derived from the running call rate, from when the
        # loop fetched per tracked user and 21 calls a cycle made any fixed wait
        # unsafe. The batch play count lookup replaced those with one call, so a
        # cycle is now that plus a fetch for each user that played - about 1.3
        # calls, measured 33-36/min. Waiting a fixed gap on top of the gate call
        # put the real period at ~2.1s, so this is the period itself and the
        # wait is whatever is left of it - the gate is absorbed rather than
        # added. At 1.5s that is ~40 gate calls a minute, ~46 with the fetches.
        # Waiting is where detection latency goes after all: play_count moves
        # before /recent publishes it, so a play takes two or three cycles to
        # pick up (measured: 100 cycles for 33 detections) and each one costs a
        # full period.
        self.cycle_period = 1.5
        # Backoff after the loop throws, and the gap that counts as a stall
        # worth logging
        self.max_sleep_duration = 5
        # Floor under the leftover wait, so a slow gate stretches the period
        # instead of chaining cycles back to back
        self.min_sleep_duration = 0.2
        self.max_concurrent_lookups = 5
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_lookups)
        # Catch-up cap when a user's play count jumped by more than one
        # between cycles; keeps one user from dominating a cycle
        self.max_scores_per_check = 5
        self._warned_channels: set[int] = set()
        self._play_counts: dict[int, int] = {}
        # Passes waiting to be built and sent. Posting a score takes ~10s in
        # the pp calculator, so it runs in its own task - the tracking loop
        # would otherwise go blind to everyone else's plays for that long
        self._post_queue: asyncio.Queue = asyncio.Queue()

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
        delta = (
            observed_play_count - last_count
            if observed_play_count is not None and last_count is not None
            else None
        )
        if delta is None:
            fetch_limit = 1
        else:
            fetch_limit = max(1, min(delta, self.max_scores_per_check))

        queued_at = time.monotonic()
        async with self.request_semaphore:
            sem_wait = time.monotonic() - queued_at
            fetch_start = time.monotonic()
            check_completed, new_scores = await is_new_score(
                self.db, user_id, limit=fetch_limit
            )
            fetch_s = time.monotonic() - fetch_start

        if check_completed and observed_play_count is not None:
            if delta is None or delta <= 0:
                # First sighting, or a stat recalculation - nothing to wait for
                self._play_counts[user_id] = observed_play_count
            else:
                # Advance the count only over plays that actually turned up -
                # `play_count` moves a moment before `/recent` publishes, and
                # committing past an unpublished play strands it until the
                # user's next play (measured: one-behind detection chains
                # under retry-spam). The shortfall keeps the user re-checked
                # every cycle until the play appears. Plays beyond the fetch
                # cap are dropped deliberately and do not hold the count back.
                expected = min(delta, self.max_scores_per_check)
                shortfall = max(expected - len(new_scores), 0)
                self._play_counts[user_id] = observed_play_count - shortfall

        # Everything is stored, only passes are posted - handed to the posting
        # worker so this task (and with it the tracking cycle) stays fast
        scores = [score for score in new_scores if score.passed]
        if not scores:
            return
        logging.info(
            f"[lag] queued user={user_id} delta={delta} limit={fetch_limit} "
            f"sem_wait={sem_wait:.1f}s fetch={fetch_s:.1f}s n={len(scores)}"
        )
        for score in scores:
            self._post_queue.put_nowait((score, channels))

    async def post_scores(self):
        """
        Builds and sends queued score posts, one at a time, in the order the
        plays happened. Runs as its own task so the ~10s calculator round trip
        per pass never stops the tracking loop from sampling play counts.
        """
        while not self.bot.is_closed():
            score, channels = await self._post_queue.get()
            try:
                build_start = time.monotonic()
                view = await create_score_view(self.db, score)
                build_s = time.monotonic() - build_start

                send_start = time.monotonic()
                for channel in channels:
                    try:
                        await channel.send(view=view)
                    except discord.HTTPException:
                        # Missing permissions or the like, don't let one channel
                        # stop the score from reaching the remaining ones
                        logging.exception(
                            f"Failed to send score embed to '{channel.id}'"
                        )
                    await asyncio.sleep(0.1)  # Avoid hitting rate limits.
                send_s = time.monotonic() - send_start

                # `score_ended_at` is naive UTC, same as everything in the db
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                age = (
                    f"{(now - score.score_ended_at).total_seconds():.1f}"
                    if score.score_ended_at is not None
                    else "n/a"
                )
                logging.info(
                    f"[lag] posted user={score.user_id} build={build_s:.1f}s "
                    f"send={send_s:.1f}s age={age}s"
                )
            except Exception:
                # The score is already stored; losing one post must not take
                # down the posting worker for everyone after it
                logging.exception(f"Failed to post score '{score.id}'")

    async def run_tracking_loop(self):
        """
        Main background task that checks for new scores and respects API rate limits.
        """
        await self.bot.wait_until_ready()
        # Reference kept on self - a task with no reference can be garbage
        # collected mid-run
        self._post_worker = asyncio.create_task(self.post_scores())

        last_cycle_start = None
        while not self.bot.is_closed():
            try:
                cycle_start = time.monotonic()
                # Gap between gate samples - it bounds how stale a detection can
                # be, so it is the first number to look at when posts lag
                since_last = cycle_start - last_cycle_start if last_cycle_start else 0.0
                last_cycle_start = cycle_start

                tracking_map = await self.get_tracking_channels()
                gate_start = time.monotonic()
                played_users = await self.get_played_users(list(tracking_map))
                gate_s = time.monotonic() - gate_start

                work_start = time.monotonic()
                async with asyncio.TaskGroup() as tg:
                    for user_id, observed_count in played_users.items():
                        tg.create_task(
                            self.notify_new_scores(
                                user_id, tracking_map[user_id], observed_count
                            )
                        )
                work_s = time.monotonic() - work_start

                sleep_s = max(
                    self.min_sleep_duration,
                    self.cycle_period - (time.monotonic() - cycle_start),
                )
                # Idle cycles run every couple of seconds, so logging them all
                # would drown the log - keep the ones that did work or stalled
                if played_users or since_last > self.max_sleep_duration + 5:
                    logging.info(
                        f"[lag] cycle since_last={since_last:.1f}s "
                        f"gate={gate_s:.1f}s moved={len(played_users)} "
                        f"work={work_s:.1f}s sleep={sleep_s:.1f}s "
                        f"calls={RequestCounter.requests_per_minute()}/min"
                    )
                await asyncio.sleep(sleep_s)
            except Exception:
                logging.exception("Error in tracking loop")
                # Back off instead of retrying immediately, a failure that sticks
                # around would otherwise spin the loop with no delay at all
                await asyncio.sleep(self.max_sleep_duration)


async def setup(bot):
    await bot.add_cog(ScoreTracker(bot))
