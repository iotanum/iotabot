FROM ubuntu:22.04 as base

WORKDIR /app

# Pull osu pp-calc stuff
RUN apt-get update -y && apt-get install git -y
RUN git clone --depth 1 https://github.com/ppy/osu-tools.git
RUN git clone --depth 1 https://github.com/ppy/osu.git

# Hacky tiem
# Pull only the ruleset dirs from main osu repo and branch
# TODO fix this, a lot of prereq
#COPY set_and_pull_rulesets.sh .
#RUN ./set_and_pull_rulesets.sh

FROM ubuntu:22.04 as final
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update && apt-get install -y wget curl build-essential

# Install dotnet
RUN wget https://download.visualstudio.microsoft.com/download/pr/16b0b1af-6eab-4f9e-b9a4-9b29f6a1d681/4624e54b61cae05b1025211482f9c5e9/dotnet-sdk-7.0.400-linux-arm64.tar.gz
RUN mkdir -p /usr/bin/dotnet && tar zxf dotnet-sdk-7.0.400-linux-arm64.tar.gz -C /usr/bin/dotnet
ENV DOTNET_ROOT="/usr/bin/dotnet"
ENV PATH="$PATH:/usr/bin/dotnet"
RUN echo "export PATH=$PATH:/usr/bin/dotnet" >> ~/.bashrc

# Install python
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.10 python3.10-distutils python3.10-dev

WORKDIR /app
RUN mkdir osu-tools
RUN mkdir osu
RUN mkdir wrapper

COPY --from=base /app/osu-tools /app/osu-tools
COPY --from=base /app/osu /app/osu
COPY wrapper /app/wrapper

# TODO fix pre-req csprojs, currently cloning whole repo
# Update pp-calc with latest difficulty rulesets (got from *rulesets.sh)
WORKDIR /app/osu-tools
RUN ./UseLocalOsu.sh

# Preload nuget libs and stuffs
WORKDIR /app/osu-tools/PerformanceCalculator
RUN dotnet run -- --help
RUN dotnet publish -r linux-arm64 --self-contained -p:PublishReadyToRun=true

WORKDIR /app/wrapper
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
RUN python3.9 get-pip.py
RUN pip install -r req

EXPOSE 8080

CMD ["python3.9", "-u", "server.py"]
