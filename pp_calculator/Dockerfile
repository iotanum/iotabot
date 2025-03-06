FROM ubuntu:24.04 AS base

WORKDIR /app

# Pull osu pp-calc stuff
RUN apt-get update -y && apt-get install git -y
RUN git clone --depth 1 https://github.com/ppy/osu-tools.git

FROM ubuntu:24.04 AS final
ENV DEBIAN_FRONTEND=noninteractive
ENV DOTNET_NUGET_SIGNATURE_VERIFICATION=false

# https://github.com/ppy/osu-infrastructure/wiki/Star-Rating-and-Performance-Points
# or https://github.com/ppy/osu-queue-score-statistics/commits/master/
ENV LIVE_OSU_RULESET_VERSION=2025.304.0

RUN apt-get -y update && apt-get -y upgrade && apt-get install -y software-properties-common && \
    rm -rf /var/lib/apt/lists/*

# Install dotnet 8 sdk
RUN add-apt-repository ppa:dotnet/backports
RUN apt-get update && apt-get install -y dotnet-sdk-8.0

# Install python
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.13-full

WORKDIR /app
RUN mkdir osu-tools
RUN mkdir wrapper

COPY --from=base /app/osu-tools /app/osu-tools
COPY wrapper /app/wrapper

# TODO fix pre-req csprojs, currently cloning whole repo
WORKDIR /app/osu-tools/PerformanceCalculator
RUN sed -i 's/\(PackageReference Include="ppy.osu.Game" Version="\)[^"]*/\1'"$LIVE_OSU_RULESET_VERSION"'/' PerformanceCalculator.csproj && \
    sed -i 's/\(PackageReference Include="ppy.osu.Game.Rulesets.Osu" Version="\)[^"]*/\1'"$LIVE_OSU_RULESET_VERSION"'/' PerformanceCalculator.csproj && \
    sed -i 's/\(PackageReference Include="ppy.osu.Game.Rulesets.Taiko" Version="\)[^"]*/\1'"$LIVE_OSU_RULESET_VERSION"'/' PerformanceCalculator.csproj && \
    sed -i 's/\(PackageReference Include="ppy.osu.Game.Rulesets.Catch" Version="\)[^"]*/\1'"$LIVE_OSU_RULESET_VERSION"'/' PerformanceCalculator.csproj && \
    sed -i 's/\(PackageReference Include="ppy.osu.Game.Rulesets.Mania" Version="\)[^"]*/\1'"$LIVE_OSU_RULESET_VERSION"'/' PerformanceCalculator.csproj

# Preload nuget libs and stuffs
RUN dotnet run -- simulate osu --help
RUN dotnet publish -r linux-arm64 --self-contained -p:PublishReadyToRun=true

WORKDIR /app/wrapper
RUN python3.13 -m ensurepip --upgrade && python3.13 -m pip install --upgrade pip && python3.13 -m pip install -r req

EXPOSE 8080

CMD ["python3.13", "-u", "server.py"]
