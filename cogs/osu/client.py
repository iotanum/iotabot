import asyncio
import logging
from typing import Optional

import aiohttp
from ossapi import (Beatmap, Beatmapset, GameMode, OssapiAsync, Score,
                    ScoreType, User)

from app.environment import APP_CONFIG
from cogs.osu.shared_state import RequestCounter

api = OssapiAsync(
    int(APP_CONFIG.get("OSU_CLIENT_ID")), APP_CONFIG.get("OSU_CLIENT_SECRET")
)


async def get_user(user: str | int) -> Optional[User]:
    try:
        result = await api.user(user, mode=GameMode.OSU)
        RequestCounter.increment()
        return result
    except ValueError:
        return


async def get_user_highscores(user_id: int, limit: int = 10) -> Optional[list[Score]]:
    try:
        scores = await api.user_scores(
            user_id,
            type=ScoreType.BEST,
            mode=GameMode.OSU,
            limit=limit,
        )
        RequestCounter.increment()

        if scores:
            return scores
    except aiohttp.client_exceptions.ContentTypeError:
        logging.error(f"ContentTypeError for '{user_id}'")
        return
    except aiohttp.client_exceptions.ClientConnectorError:
        logging.error(f"ClientConnectorError, {user_id}")
        return
    except asyncio.TimeoutError:
        logging.error(f"TimeoutError, {user_id}")
        return


async def get_recent_user_score(
    user_id: int, include_fails: bool = True, limit: int = 1
) -> Optional[Score]:
    try:
        score = await api.user_scores(
            user_id,
            type=ScoreType.RECENT,
            include_fails=include_fails,
            mode=GameMode.OSU,
            limit=limit,
        )
        RequestCounter.increment()

        if score:
            return score[0]
    except aiohttp.client_exceptions.ContentTypeError:
        logging.error(f"ContentTypeError for '{user_id}'")
        return
    except aiohttp.client_exceptions.ClientConnectorError:
        logging.error(f"ClientConnectorError, {user_id}")
        return
    except asyncio.TimeoutError:
        logging.error(f"TimeoutError, {user_id}")
        return


async def get_beatmap(beatmap_id: int) -> Beatmap:
    result = await api.beatmap(beatmap_id=beatmap_id)
    RequestCounter.increment()
    return result


async def get_beatmapset(beatmapset_id: int) -> Beatmapset:
    result = await api.beatmapset(beatmapset_id=beatmapset_id)
    RequestCounter.increment()

    return result
