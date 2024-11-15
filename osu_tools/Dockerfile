FROM ubuntu:24.04 AS base

WORKDIR /app

# Pull osu pp-calc stuff
RUN apt-get update -y && apt-get install git -y
RUN git clone --depth 1 https://github.com/ppy/osu-tools.git
RUN git clone --depth 1 https://github.com/ppy/osu.git

FROM ubuntu:24.04 AS final
ENV DEBIAN_FRONTEND=noninteractive

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
RUN mkdir osu
RUN mkdir wrapper

COPY --from=base /app/osu-tools /app/osu-tools
COPY --from=base /app/osu /app/osu
COPY wrapper /app/wrapper

# TODO fix pre-req csprojs, currently cloning whole repo
WORKDIR /app/osu-tools
RUN ./UseLocalOsu.sh

# Preload nuget libs and stuffs
WORKDIR /app/osu-tools/PerformanceCalculator
RUN dotnet run -- --help
# -r linux-arm64
RUN dotnet publish --self-contained -p:PublishReadyToRun=true

WORKDIR /app/wrapper
RUN python3.13 -m ensurepip --upgrade && python3.13 -m pip install --upgrade pip && python3.13 -m pip install -r req

EXPOSE 8080

CMD ["python3.13", "-u", "server.py"]
