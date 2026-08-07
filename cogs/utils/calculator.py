import asyncio
import logging

import aiohttp

from app.environment import APP_CONFIG
from app.models.scores import Scores

CALC_HOST = APP_CONFIG.get("CALC_HOST", "localhost")
CALC_PORT = APP_CONFIG.get("CALC_PORT", "8080")
CALC_URL = f"http://{CALC_HOST}:{CALC_PORT}/calculate"

# One request means five dotnet simulations, each pegging a core on the Pi that
# also runs this bot and the database. Two in flight keeps the calculator's
# own 2-process semaphore fed (~15% throughput, measured) at no extra CPU -
# the sidecar's MAX_CONCURRENT_SIMULATIONS stays the real cap.
_calc_semaphore = asyncio.Semaphore(2)


async def calculate_scores(score: Scores, checksum: str | None = None) -> dict:
    """
    Sends a POST request to calculate scores based on the provided score details.

    `checksum` is the beatmap's md5. The calculator reuses results between plays
    of the same map, and revalidates its own copy of the .osu file, so without
    one it recomputes everything from scratch rather than risk a stale answer.
    """
    # Build request body with conditionally included fields
    req_body = {
        "beatmap_id": str(score.beatmap_id),
        "accuracy": f"{100 * (score.accuracy or 0):.2f}",
        "combo": str(score.max_combo),
        **({"goods": str(score.ok)} if score.ok else {}),
        **({"mehs": str(score.meh)} if score.meh else {}),
        **({"misses": str(score.miss)} if score.miss else {}),
        **({"mod": score.mods_list} if score.mods_list else {}),
        **({"checksum": checksum} if checksum else {}),
    }

    headers = {"Content-Type": "application/json"}

    async with _calc_semaphore, aiohttp.ClientSession() as session:
        try:
            async with session.post(
                CALC_URL, json=req_body, headers=headers, ssl=False
            ) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors
                resp_json = await response.json()
                # Just the pp values - the full response is every attribute of
                # five simulations, about 8KB a line
                logging.info(
                    f"Calc for beatmap '{score.beatmap_id}': "
                    + " ".join(
                        f"{key}={resp_json[key]['p_attr']['pp']:.2f}"
                        for key in ("score", "if_fc", "100", "95", "90")
                        if key in resp_json
                    )
                )
                return resp_json
        except aiohttp.ClientError as e:
            logging.error(f"Error while calculating scores (ClientError): {e}")
            raise e
        except Exception as e:
            logging.error(f"Unexpected error while calculating scores: {e}")
            raise e


async def calculate_bpm(mods: list[str] | None, bpm: float) -> float:
    """
    Adjusts the BPM based on the mods applied.
    """
    if not mods:
        return bpm

    if "HT" in mods:
        return bpm * 0.75
    if any(mod in mods for mod in ["DT", "NC"]):
        return bpm * 1.5

    return bpm
