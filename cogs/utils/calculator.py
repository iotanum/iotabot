import asyncio
import logging

import aiohttp

from app.environment import APP_CONFIG
from app.models.scores import Scores

CALC_HOST = APP_CONFIG.get("CALC_HOST", "localhost")
CALC_PORT = APP_CONFIG.get("CALC_PORT", "8080")
CALC_URL = f"http://{CALC_HOST}:{CALC_PORT}/"

# The calculator serves requests concurrently and does not limit them itself, so
# this is the only cap. One request is five simulations sharing a single
# difficulty calculation, which costs about one core for a fraction of a second.
_calc_semaphore = asyncio.Semaphore(2)


def fix_mods(mods: list) -> list:
    fixed_mods = list()

    for mod in mods:
        fixed_mods += ["--mod", mod]

    return fixed_mods


def simulate_args(params: dict) -> list:
    """
    Turns one simulation's parameters into the arguments `simulate osu` takes.

    Anything absent is left off the command, which is what makes the hypothetical
    scores differ from the played one - no `--combo`, for instance, means the
    calculator uses the beatmap maximum.
    """
    command = [params["beatmap_id"]]

    mod = params.get("mod")
    accuracy = params.get("accuracy")
    combo = params.get("combo")
    goods = params.get("goods")
    mehs = params.get("mehs")
    misses = params.get("misses")

    if mod:
        command = command + fix_mods(mod)
    if accuracy:
        command += ["--accuracy", str(accuracy)]
    if combo:
        command += ["--combo", str(combo)]
    if goods:
        command += ["--goods", str(goods)]
    if mehs:
        command += ["--mehs", str(mehs)]
    if misses:
        command += ["--misses", str(misses)]

    command.append("--json")

    return command


async def calculate_scores(score: Scores, checksum: str | None = None) -> dict:
    """
    Sends a POST request to calculate scores based on the provided score details.

    `checksum` is the beatmap's md5. The calculator only ever downloads a .osu it
    does not already have, so without one it cannot tell that a map has been
    reworked and would keep reporting the difficulty it used to have.
    """
    # Build the played score with conditionally included fields
    body = {
        "beatmap_id": str(score.beatmap_id),
        "accuracy": f"{100 * (score.accuracy or 0):.2f}",
        "combo": str(score.max_combo),
        **({"goods": str(score.ok)} if score.ok else {}),
        **({"mehs": str(score.meh)} if score.meh else {}),
        **({"misses": str(score.miss)} if score.miss else {}),
        **({"mod": score.mods_list} if score.mods_list else {}),
    }

    runs = {"score": simulate_args(body)}

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

        # Give 0 misses and the beatmap maximum combo, calculator will figure
        # out 100s and 50s
        body_copy["misses"] = 0
        del body_copy["combo"]

        runs[str(acc)] = simulate_args(body_copy)

    # An "if_fc" score - keeps the played 100s/50s, so it belongs to this play
    if_fc = body.copy()
    del if_fc["accuracy"]
    del if_fc["combo"]
    if_fc["misses"] = 0
    runs["if_fc"] = simulate_args(if_fc)

    req_body: dict = {"runs": runs}
    if checksum:
        req_body["checksum"] = checksum

    headers = {"Content-Type": "application/json"}

    async with _calc_semaphore, aiohttp.ClientSession() as session:
        try:
            async with session.post(
                CALC_URL, json=req_body, headers=headers, ssl=False
            ) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors
                resp_json = await response.json()
        except aiohttp.ClientError as e:
            logging.error(f"Error while calculating scores (ClientError): {e}")
            raise e
        except Exception as e:
            logging.error(f"Unexpected error while calculating scores: {e}")
            raise e

    # Manipulate the json to be more readable
    scores = {
        name: {
            **result.get("score", {}),
            "p_attr": result.get("performance_attributes", {}),
            "d_attr": result.get("difficulty_attributes", {}),
        }
        for name, result in resp_json.items()
    }

    # Just the pp values - the full response is every attribute of five
    # simulations, about 8KB a line
    logging.info(
        f"Calc for beatmap '{score.beatmap_id}': "
        + " ".join(
            f"{key}={scores[key]['p_attr']['pp']:.2f}"
            for key in ("score", "if_fc", "100", "95", "90")
            if key in scores
        )
    )

    return scores


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
