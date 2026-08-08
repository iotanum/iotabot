FROM mcr.microsoft.com/dotnet/sdk:8.0 AS base

WORKDIR /app

# Pull osu pp-calc stuff
RUN git clone https://github.com/ppy/osu-tools.git


FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

# https://github.com/ppy/osu-infrastructure/wiki/Star-Rating-and-Performance-Points
# or https://github.com/ppy/osu-queue-score-statistics/commits/master/
# or https://github.com/ppy/osu-queue-score-statistics/blob/master/osu.Server.Queues.ScoreStatisticsProcessor/osu.Server.Queues.ScoreStatisticsProcessor.csproj#L17-L21
ENV LIVE_OSU_RULESET_VERSION=2026.730.0
WORKDIR /app
COPY --from=base /app/osu-tools /app/osu-tools

COPY Directory.Build.targets ./

# The runtime to build for, and what gets left out of the output, are both
# declared in CalculatorServer.csproj - restore and publish read them from there
COPY server/CalculatorServer.csproj server/
RUN dotnet restore server/CalculatorServer.csproj \
        -p:LiveOsuRulesetVersion=${LIVE_OSU_RULESET_VERSION}

COPY server/CalculatorServer.cs server/

# debug cuz jit is faster than compiled binaries on raspi
RUN dotnet publish server/CalculatorServer.csproj -c Debug --no-restore \
        -p:LiveOsuRulesetVersion=${LIVE_OSU_RULESET_VERSION} -o /app/out


FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final

ENV ASPNETCORE_URLS=http://0.0.0.0:8080
ENV BEATMAP_CACHE_DIR=/var/cache/osu-beatmaps

# needed only for the healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/out ./

EXPOSE 8080

# `/` answers 503 until warm-up finishes, so a replaced container is not sent
# traffic while it is still ~15x slower than it will be a minute later.
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl --fail --silent --output /dev/null http://localhost:8080/ || exit 1

ENTRYPOINT ["dotnet", "CalculatorServer.dll"]
