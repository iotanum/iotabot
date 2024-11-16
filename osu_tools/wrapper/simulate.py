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


def simulate_score(beatmap_id: str, accuracy: str = None, combo: str = None, mods: list = None, goods: str = None,
                   mehs: str = None, misses: str = None):
    command = OSU_SIMULATE_CMD.copy()

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
    result = result.stdout
    result = result.split("\n")
    print(command)
    print(result)
    for msg in result:
        if msg.lower().startswith('{"score'):
            result = msg
    return json.loads(result)
