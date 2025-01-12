import logging

from typing import Optional

from ossapi import Score
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scores import Scores
from app.models.user import User
from cogs.osu.client import get_recent_user_score


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


async def is_new_score(db_sess: AsyncSession, user_id: int) -> Optional[Scores]:
    """
    Checks if a new score is available for the user and adds it if it is not already in the database.
    """
    import time
    start = time.time()
    new_score = await get_recent_user_score(user_id, include_fails=True)
    logging.info(f"Time taken to get recent user score: {time.time() - start}, {user_id}")
    start = time.time()
    if not new_score:
        return None

    # Check if the score is already in the database
    db_score = await Scores.get(
        db_sess, user_id, new_score.beatmap.id, new_score.ended_at
    )
    logging.info(f"Time taken to get score from database: {time.time() - start}, {user_id}")
    start = time.time()
    if not db_score:
        logging.info(f"New score found for user_id '{user_id}' - '{new_score.beatmap.id}', at '{new_score.ended_at}'")
        # save all scores, send only passed ones
        score = await add_score(db_sess, new_score)
        if score.passed:
            return score
        return None
    else:
        # Clean old scores if the new score already exists
        await Scores.clean_old_scores(db_sess, user_id)
        logging.info(f"Time taken to clean old scores: {time.time() - start}, {user_id}")
        return None
