import asyncio
import logging
import time
from typing import Optional

import aiohttp
from ossapi import GameMode, OssapiAsync, Score, ScoreType, User
from ossapi.models import UserCompact

from app.environment import APP_CONFIG
from cogs.osu.shared_state import RequestCounter

OSU_CLIENT_ID = APP_CONFIG.get("OSU_CLIENT_ID")
OSU_CLIENT_SECRET = APP_CONFIG.get("OSU_CLIENT_SECRET")
if not OSU_CLIENT_ID or not OSU_CLIENT_SECRET:
    raise RuntimeError("OSU_CLIENT_ID and OSU_CLIENT_SECRET must be set")

api = OssapiAsync(int(OSU_CLIENT_ID), OSU_CLIENT_SECRET)

# `GET /users` returns at most this many users per request
USERS_BATCH_SIZE = 50

DEFAULT_RATE_LIMIT_COOLDOWN = 30.0
_rate_limited_until = 0.0


async def _call_api(coro, *, log_id):
    """
    Runs an osu! API call, skipping it entirely while we're in a rate-limit
    cooldown, and normalizing transient network/API errors to None.
    """
    global _rate_limited_until

    if time.monotonic() < _rate_limited_until:
        return None

    try:
        result = await coro
        RequestCounter.increment()
        return result
    except aiohttp.ClientResponseError as e:
        if e.status == 429:
            retry_after = DEFAULT_RATE_LIMIT_COOLDOWN
            header_value = e.headers.get("Retry-After") if e.headers else None
            if header_value:
                try:
                    retry_after = float(header_value)
                except ValueError:
                    pass
            _rate_limited_until = time.monotonic() + retry_after
            logging.error(
                f"osu! API rate limited us (429) on '{log_id}'; "
                f"pausing osu! API calls for {retry_after:.0f}s"
            )
        else:
            logging.error(f"{type(e).__name__} ({e.status}) for '{log_id}'")
        return None
    except aiohttp.client_exceptions.ClientConnectorError:
        logging.error(f"ClientConnectorError, {log_id}")
        return None
    except aiohttp.client_exceptions.ServerDisconnectedError:
        logging.error(f"ServerDisconnectedError, {log_id}")
        return None
    except asyncio.TimeoutError:
        logging.error(f"TimeoutError, {log_id}")
        return None


async def get_user(user: str | int) -> Optional[User]:
    try:
        return await _call_api(api.user(user, mode=GameMode.OSU), log_id=user)
    except ValueError:
        return None


async def get_users(user_ids: list[int]) -> Optional[list[UserCompact]]:
    """
    Batch user lookup, `user_ids` must be at most `USERS_BATCH_SIZE` long.
    Returns `None` when the call fails; restricted users are absent from the
    result.
    """
    return await _call_api(
        api.users(user_ids), log_id=f"users batch of {len(user_ids)}"
    )


async def get_user_highscores(user_id: int, limit: int = 10) -> Optional[list[Score]]:
    scores = await _call_api(
        api.user_scores(user_id, type=ScoreType.BEST, mode=GameMode.OSU, limit=limit),
        log_id=user_id,
    )
    return scores or None


async def get_recent_user_scores(
    user_id: int, include_fails: bool = True, limit: int = 1
) -> Optional[list[Score]]:
    """
    Returns `None` when the fetch failed and `[]` when it succeeded but the
    user has nothing in the API's recent window, so callers can tell a dead
    check apart from a quiet user.
    """
    return await _call_api(
        api.user_scores(
            user_id,
            type=ScoreType.RECENT,
            include_fails=include_fails,
            mode=GameMode.OSU,
            limit=limit,
        ),
        log_id=user_id,
    )
