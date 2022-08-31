from typing import List
from subprocess import run
import subprocess

import os
import json

PP_CALC_DIR = "/app/osu-tools/PerformanceCalculator"
DOTNET_VER = "net6.0"
DOTNET_PUBLISH_RUNTIME = "linux-arm64"
PUBLISHED_CALC = f"bin/Debug/{DOTNET_VER}/{DOTNET_PUBLISH_RUNTIME}/publish/PerformanceCalculator"
OSU_SIMULATE_CMD = [PUBLISHED_CALC, "simulate", "osu"]


def fix_mods(mods: str) -> List:
    fixed_mods = list()

    # delimit mods by 2 chara
    n = 2
    mods = [mods[i:i+n] for i in range(0, len(mods), n)]
    for mod in mods:
        fixed_mods.append(f"--mod {mod}")

    return fixed_mods


def simulate_score(beatmap_id: str, accuracy: str, combo: str,
                   mods: str = None, goods: str = None, mehs: str = None, misses: str = None):
    command = OSU_SIMULATE_CMD.copy()

    command.append(beatmap_id)
    command.append(f"--accuracy {accuracy}")
    command = command + fix_mods(mods)
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
