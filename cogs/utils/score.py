import logging
from datetime import datetime, timezone

from ossapi import Score
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scores import Scores
from app.models.user import User
from cogs.osu.client import get_recent_user_scores


async def add_score(db_sess: AsyncSession, new_api_score: Score) -> Scores:
    """
    Adds a new score to the database and updates the user information.
    """
    # Add the score to the database
    score = await Scores.add(db_sess, new_api_score)

    # Update user information if it has changed
    await update_user(db_sess, new_api_score)

    return score


async def update_user(db: AsyncSession, score: Score):
    """
    Updates user information based on the given score.
    """
    user = await User.get(db, score.user_id)
    if user:
        await User.update_from_score(db, score)


async def is_new_score(
    db_sess: AsyncSession, user_id: int, limit: int = 1
) -> tuple[bool, list[Scores]]:
    """
    Checks if new scores are available for the user and adds the ones not
    already in the database. Returns `(check_completed, new_scores)`:
    `check_completed` is False only when the score fetch failed, telling
    the caller to re-check the user instead of advancing its play-count
    bookkeeping; `new_scores` holds everything just stored, fails included,
    oldest first.
    """
    recent_scores = await get_recent_user_scores(
        user_id, include_fails=True, limit=limit
    )
    if recent_scores is None:
        # Fetch failed - whatever the user played is still unaccounted for
        return False, []
    if not recent_scores:
        # Fetch fine, the user has nothing in the API's recent window
        return True, []

    new_scores = []
    # Oldest first, so a burst of scores is posted in the order it was played
    for new_score in reversed(recent_scores):
        db_score = await Scores.get(
            db_sess, user_id, new_score.beatmap.id, new_score.ended_at
        )
        if db_score:
            continue
        # Age at detection: how long the play sat between finishing and this
        # fetch returning it. It splits osu!'s own propagation from our loop
        detect_age = (
            datetime.now(timezone.utc) - new_score.ended_at
        ).total_seconds()
        logging.info(
            f"New score found for user_id '{user_id}' - '{new_score.beatmap.id}', "
            f"at '{new_score.ended_at}' [lag] detect_age={detect_age:.1f}s "
            f"passed={new_score.passed}"
        )
        new_scores.append(await add_score(db_sess, new_score))

    # With the play-count gate, adds are the common case, so retention runs
    # on every completed check that found scores in the window
    await Scores.clean_old_scores(db_sess, user_id)
    return True, new_scores
