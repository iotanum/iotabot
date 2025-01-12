import logging

import aiohttp

from app.models.scores import Scores

CALC_URL = "http://pp_calc:8080/calculate"


async def calculate_scores(score: Scores) -> dict:
    """
    Sends a POST request to calculate scores based on the provided score details.
    """
    # Build request body with conditionally included fields
    req_body = {
        "beatmap_id": str(score.beatmap_id),
        "accuracy": f"{100 * score.accuracy:.2f}",
        "combo": str(score.max_combo),
        **({"goods": str(score.ok)} if score.ok else {}),
        **({"mehs": str(score.meh)} if score.meh else {}),
        **({"misses": str(score.miss)} if score.miss else {}),
        **({"mod": score.mods_list} if score.mods_list else {}),
    }

    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                CALC_URL, json=req_body, headers=headers, ssl=False
            ) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors
                resp_json = await response.json()
                logging.info(f"Calc response: {resp_json}")
                return resp_json
        except aiohttp.ClientError as e:
            logging.error(f"Error while calculating scores (ClientError): {e}")
            raise e
        except Exception as e:
            logging.error(f"Unexpected error while calculating scores: {e}")
            raise e


async def calculate_bpm(mods: list[str], bpm: float) -> float:
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
