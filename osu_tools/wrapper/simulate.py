from typing import List
from subprocess import run

import os
import json

from dotnet_config import *


def fix_mods(mods: list) -> List:
    fixed_mods = list()

    for mod in mods:
        fixed_mods.append(f"--mod {mod}")

    return fixed_mods


def simulate_score(beatmap_id: str, params: dict):
    command = OSU_SIMULATE_CMD.copy()

    beatmap_id = params.get('beatmap_id')
    accuracy = params.get('accuracy')
    combo = params.get('combo')
    mods = params.get('mods')
    goods = params.get('goods')
    mehs = params.get('mehs')
    misses = params.get('misses')

    command.append(beatmap_id)

    if mods:
        command = command + fix_mods(mods)
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

    os.chdir(PP_CALC_DIR)
    result = run(command, check=True, capture_output=True, text=True)

    score = result.stdout.split("\n")
    if score[0].lower().startswith('downloading'):
        score.pop(0)

    score_dict = json.loads(" ".join(score))["score"]
    return score_dict
