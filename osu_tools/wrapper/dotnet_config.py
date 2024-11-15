PP_CALC_DIR = "/app/osu-tools/PerformanceCalculator"
DOTNET_VER = "net8.0"
DOTNET_PUBLISH_RUNTIME = "linux-arm64"
PUBLISHED_CALC = f"bin/Debug/{DOTNET_VER}/PerformanceCalculator"
OSU_SIMULATE_CMD = [PUBLISHED_CALC, "simulate", "osu"]
