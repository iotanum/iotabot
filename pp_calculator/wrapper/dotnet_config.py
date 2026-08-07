import os

# Where osu-tools lives. The calculator is started from here, and both its
# binary and its beatmap cache are resolved relative to it
PP_CALC_DIR = os.environ.get("PP_CALC_DIR", "/app/osu-tools/PerformanceCalculator")
DOTNET_VER = os.environ.get("DOTNET_VER", "net8.0")
PUBLISHED_CALC = f"bin/Debug/{DOTNET_VER}/PerformanceCalculator"
OSU_SIMULATE_CMD = [PUBLISHED_CALC, "simulate", "osu"]

# osu-tools writes downloaded maps to a *relative* "cache" directory
# (ProcessorWorkingBeatmap.FromFileOrId), so this has to stay derived from
# PP_CALC_DIR rather than be set on its own - otherwise the wrapper and the
# calculator would be looking at two different folders
BEATMAP_CACHE_DIR = os.path.join(PP_CALC_DIR, "cache")
BEATMAP_URL = os.environ.get("BEATMAP_URL", "https://osu.ppy.sh/osu/{}")
