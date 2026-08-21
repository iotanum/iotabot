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


def fix_mods(mods: list, settings: dict | None = None) -> list:
    """
    Turns mods and their lazer settings into the arguments the command takes.

    A setting is `acronym_key=value`, which is how the command's own parser
    hands it to the mod. Booleans go over as `True`, which parses the same as
    `true` on the other side.
    """
    fixed_mods = list()

    for mod in mods:
        fixed_mods += ["--mod", mod]

        for key, value in (settings or {}).get(mod, {}).items():
            fixed_mods += ["--mod-option", f"{mod}_{key}={value}"]

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
    large_tick_misses = params.get("large_tick_misses")
    slider_tail_misses = params.get("slider_tail_misses")

    if mod:
        command = command + fix_mods(mod, params.get("mod_settings"))
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
    if large_tick_misses:
        command += ["--large-tick-misses", str(large_tick_misses)]
    if slider_tail_misses:
        command += ["--slider-tail-misses", str(slider_tail_misses)]

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
        **({"mod_settings": score.mod_settings} if score.mod_settings else {}),
        # Only ever set on a lazer play - see `Scores.filter_valid_kwargs`
        **(
            {"large_tick_misses": score.large_tick_miss}
            if score.large_tick_miss
            else {}
        ),
        **(
            {"slider_tail_misses": score.slider_tail_miss}
            if score.slider_tail_miss
            else {}
        ),
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

        # A clean play at a given accuracy drops no slider tails or large ticks
        # either, so the played counts have no place in these
        body_copy.pop("large_tick_misses", None)
        body_copy.pop("slider_tail_misses", None)

        # Give 0 misses and the beatmap maximum combo, calculator will figure
        # out 100s and 50s
        body_copy["misses"] = 0
        del body_copy["combo"]

        runs[str(acc)] = simulate_args(body_copy)

    # An "if_fc" score - keeps the played 100s/50s, so it belongs to this play.
    # Dropped slider tails stay for the same reason; large ticks break combo, so
    # a full combo cannot have missed any and they go
    if_fc = body.copy()
    del if_fc["accuracy"]
    del if_fc["combo"]
    if_fc.pop("large_tick_misses", None)
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


# What each rate mod does to the speed of a play when its rate is left alone.
# DC and NC are lazer's daycore and nightcore - the same rates as HT and DT
# under acronyms of their own, and leaving DC out left daycore plays reading at
# the map's unmodified bpm.
#
# Lazer lets the rate be dialled off these defaults, anywhere from 0.5x to 2x,
# which is what `speed_change` in a score's mod settings carries
DEFAULT_RATES = {"DT": 1.5, "NC": 1.5, "HT": 0.75, "DC": 0.75}

# What a stat is worth in milliseconds at 0, at 5 and at 10, from osu!'s
# OsuHitObject (the approach window) and OsuHitWindows (the great window)
AR_MILLISECONDS = (1800.0, 1200.0, 450.0)
OD_MILLISECONDS = (80.0, 50.0, 20.0)

# What HR and EZ do to AR, OD, CS and HP, from osu!'s ModHardRock and
# OsuModEasy. Nothing passes 10, which only ever binds on the way up, and the
# two are mutually exclusive, so at most one of them touches a play
STAT_MULTIPLIERS = {"HR": (1.4, 1.4, 1.3, 1.4), "EZ": (0.5, 0.5, 0.5, 0.5)}


def mod_rate(mods: list[str] | None, settings: dict | None = None) -> float:
    """
    The speed multiplier a set of mods plays at, at its dialled rate if it has
    one and at the mod's default otherwise.
    """
    if not mods:
        return 1.0

    for mod, rate in DEFAULT_RATES.items():
        if mod in mods:
            return (settings or {}).get(mod, {}).get("speed_change", rate)

    return 1.0


def _stat_to_milliseconds(stat: float, low: float, mid: float, high: float) -> float:
    """osu!'s IBeatmapDifficultyInfo.DifficultyRange."""
    if stat > 5:
        return mid + (high - mid) * (stat - 5) / 5
    if stat < 5:
        return mid + (mid - low) * (stat - 5) / 5
    return mid


def _stat_from_milliseconds(ms: float, low: float, mid: float, high: float) -> float:
    """osu!'s IBeatmapDifficultyInfo.InverseDifficultyRange."""
    if (ms > mid) == (high > mid):
        return (ms - mid) / (high - mid) * 5 + 5
    return (ms - mid) / (mid - low) * 5 + 5


def adjusted_difficulty(
    mods: list[str] | None,
    ar: float,
    od: float,
    cs: float,
    hp: float,
    settings: dict | None = None,
) -> tuple[float, float, float, float]:
    """
    The map's four stats as the play actually met them.

    HR and EZ scale the stats themselves. The rate mods leave them where they
    are and move the windows they stand for instead, so AR and OD go out to
    milliseconds, take the rate, and come back - which is what makes an AR9 map
    read as AR10.3 under DT. CS and HP stand for no window, so no rate reaches
    them.
    """
    mods = mods or []

    for mod, (ar_x, od_x, cs_x, hp_x) in STAT_MULTIPLIERS.items():
        if mod in mods:
            ar, od, cs, hp = (
                min(ar * ar_x, 10.0),
                min(od * od_x, 10.0),
                min(cs * cs_x, 10.0),
                min(hp * hp_x, 10.0),
            )
            break

    rate = mod_rate(mods, settings)
    if rate != 1.0:
        ar = _stat_from_milliseconds(
            _stat_to_milliseconds(ar, *AR_MILLISECONDS) / rate, *AR_MILLISECONDS
        )
        od = _stat_from_milliseconds(
            _stat_to_milliseconds(od, *OD_MILLISECONDS) / rate, *OD_MILLISECONDS
        )

    return ar, od, cs, hp


async def calculate_bpm(
    mods: list[str] | None, bpm: float, settings: dict | None = None
) -> float:
    """
    Adjusts the BPM based on the mods applied.
    """
    return bpm * mod_rate(mods, settings)
