import json
import os
from subprocess import run
from typing import List

import dotnet_config as app_config


def fix_mods(mods: list) -> List:
    fixed_mods = list()

    for mod in mods:
        fixed_mods.append(f"--mod {mod}")

    return fixed_mods


def simulate_score(params: dict):
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

    os.chdir(app_config.PP_CALC_DIR)
    "bin/Debug/net8.0/PerformanceCalculator simulate osu 4658845 --accuracy 92 --combo 235 --goods 355 --mehs 1 --misses 11 --json"

    print("Calculating:", " ".join(command), "\n    with body:", params)
    result = run(command, check=True, capture_output=True, text=True)

    score = result.stdout.split("\n")
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
