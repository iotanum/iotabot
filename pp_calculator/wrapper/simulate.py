import asyncio
import json
from typing import List

import dotnet_config as app_config

# Each simulation is a dotnet process that pegs a core while it calculates
# difficulty. The Pi shares its four cores with the bot and postgres, so only
# let a couple of them run at a time.
MAX_CONCURRENT_SIMULATIONS = 2
_simulation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SIMULATIONS)


def fix_mods(mods: list) -> List:
    fixed_mods = list()

    for mod in mods:
        fixed_mods.append(f"--mod {mod}")

    return fixed_mods


async def simulate_score(params: dict):
    command = app_config.OSU_SIMULATE_CMD.copy()

    beatmap_id = params.get("beatmap_id")
    accuracy = params.get("accuracy")
    combo = params.get("combo")
    mod = params.get("mod")
    goods = params.get("goods")
    mehs = params.get("mehs")
    misses = params.get("misses")

    command.append(beatmap_id)

    if mod:
        command = command + fix_mods(mod)
    if accuracy:
        command.append(f"--accuracy {accuracy}")
    if combo:
        command.append(f"--combo {combo}")
    if goods:
        command.append(f"--goods {goods}")
    if mehs:
        command.append(f"--mehs {mehs}")
    if misses:
        command.append(f"--misses {misses}")

    command.append("--json")

    # e.g. bin/Debug/net8.0/PerformanceCalculator simulate osu 4658845
    #      --accuracy 92 --combo 235 --goods 355 --mehs 1 --misses 11 --json
    print("Calculating:", " ".join(command), "\n    with body:", params)

    async with _simulation_semaphore:
        # The calculator path is relative, so it has to run from its own
        # directory - `cwd` does that per process, unlike a global chdir
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=app_config.PP_CALC_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"PerformanceCalculator exited with {process.returncode}: "
            f"{stderr.decode().strip()}"
        )

    score = stdout.decode().split("\n")
    if score[0].lower().startswith("downloading"):
        score.pop(0)
    # Manipulate the json to be more readable
    score_dict = json.loads(" ".join(score))
    score_inner = score_dict.get("score", {})
    score = {
        **score_inner,
        "p_attr": score_dict.get("performance_attributes", {}),
        "d_attr": score_dict.get("difficulty_attributes", {}),
    }

    return score
