import asyncio
import hashlib
import json
import os
import uuid
from collections import OrderedDict

import aiohttp
import dotnet_config as app_config
from aiohttp import web
from simulate import simulate_score

routes = web.RouteTableDef()

# The 100/95/90 simulations have every trace of the played score stripped out of
# their request bodies, so they depend only on the beatmap and the mods - and
# 77% of consecutive plays are retries of the same map. Bounded because the
# process is long-lived; the least recently used entry falls out first.
ACCURACY_CACHE_SIZE = 256
_accuracy_cache: OrderedDict = OrderedDict()


def cache_key(body: dict):
    """
    Identifies the (beatmap, mods) a set of hypothetical scores belongs to.

    `None` when the beatmap's checksum is unknown: a map can be reworked while
    keeping its id, so without a checksum there is no way to tell a cached
    result apart from a stale one, and nothing is reused.
    """
    checksum = body.get("checksum")
    if not checksum:
        return None
    return (str(body.get("beatmap_id")), tuple(sorted(body.get("mod") or [])), checksum)


def cached_beatmap_path(beatmap_id) -> str:
    return os.path.join(app_config.BEATMAP_CACHE_DIR, f"{beatmap_id}.osu")


def cached_beatmap_is_current(path: str, checksum: str | None) -> bool:
    """
    Whether the .osu on disk is the revision `checksum` describes. With no
    checksum to compare against, whatever is already there has to do.
    """
    if not os.path.exists(path):
        return False
    if not checksum:
        return True

    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest() == checksum


async def download_beatmap(beatmap_id, path: str):
    """Fetches a .osu and moves it into place, never leaving a partial file."""
    async with aiohttp.ClientSession() as session:
        async with session.get(app_config.BEATMAP_URL.format(beatmap_id)) as response:
            response.raise_for_status()
            data = await response.read()

    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.{uuid.uuid4().hex}.tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)
    os.replace(tmp_path, path)


async def ensure_beatmap(beatmap_id, checksum):
    """
    Keeps the calculator's copy of a beatmap current.

    osu-tools downloads a .osu only when the file is missing and never looks at
    it again, so a reworked map would keep its original difficulty for as long
    as the container lives. Fetching here also stops the simulations, which now
    all start at once, from racing each other to write the same path.
    """
    if not beatmap_id:
        return

    path = cached_beatmap_path(beatmap_id)
    if cached_beatmap_is_current(path, checksum):
        return

    try:
        await download_beatmap(beatmap_id, path)
    except Exception as e:
        # Leave whatever is on disk - the calculator fetches the beatmap itself
        # when it is missing, which is what happened before this existed
        print(f"Could not refresh beatmap {beatmap_id}: {e}")


@routes.post("/calculate")
async def calculate(request):
    body = json.loads(await request.text())

    await ensure_beatmap(body.get("beatmap_id"), body.get("checksum"))

    key = cache_key(body)
    cached = _accuracy_cache.get(key) if key else None
    if cached is not None:
        _accuracy_cache.move_to_end(key)

    # Build request bodies for the scores that did not happen. All of them drop
    # the played `combo`: with no `--combo` the calculator falls back to
    # `--percent-combo`, which defaults to 100 - the beatmap maximum, the same
    # value these used to be handed. That is what lets them run without waiting
    # for the played score to report its `max_combo` first
    possible_bodies = dict()

    if cached is None:
        for acc in [100, 95, 90]:
            body_copy = body.copy()

            # Give "possible" accuracy for the calculated score
            body_copy["accuracy"] = acc

            # Remove 100s from possible score with given accuracy
            if body_copy.get("goods"):
                del body_copy["goods"]

            # Remove 50s from possible score with given accuracy
            if body_copy.get("mehs"):
                del body_copy["mehs"]

            # Give 0 misses and the beatmap maximum combo, calculator will
            # figure out 100s and 50s
            body_copy["misses"] = 0
            del body_copy["combo"]

            # Give "acc" as key in scores_dict
            possible_bodies[acc] = body_copy

    # simulate an "if_fc" score - keeps the played 100s/50s, so it belongs to
    # this play alone and is never cached
    if_fc = body.copy()
    del if_fc["accuracy"]
    del if_fc["combo"]
    if_fc["misses"] = 0
    possible_bodies["if_fc"] = if_fc

    # Nothing depends on anything else now, so the played score runs alongside
    # the rest instead of gating them. The semaphore in simulate_score decides
    # how many actually execute at once
    result_keys = ["score", *possible_bodies]
    results = await asyncio.gather(
        simulate_score(body),
        *(simulate_score(params) for params in possible_bodies.values()),
    )
    scores_dict = dict(zip(result_keys, results))

    if cached is not None:
        scores_dict.update(cached)
    elif key:
        _accuracy_cache[key] = {acc: scores_dict[acc] for acc in [100, 95, 90]}
        while len(_accuracy_cache) > ACCURACY_CACHE_SIZE:
            _accuracy_cache.popitem(last=False)

    return web.json_response(data=scores_dict)


app = web.Application()
app.add_routes(routes)

# Guarded so the module can be imported (by tests) without starting a server
if __name__ == "__main__":
    web.run_app(app)
