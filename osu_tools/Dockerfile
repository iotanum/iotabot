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
RUN wget https://download.visualstudio.microsoft.com/download/pr/901f7928-5479-4d32-a9e5-ba66162ca0e4/d00b935ec4dc79a27f5bde00712ed3d7/dotnet-sdk-6.0.400-linux-arm64.tar.gz
RUN mkdir -p /usr/bin/dotnet && tar zxf dotnet-sdk-6.0.400-linux-arm.tar.gz -C /usr/bin/dotnet
ENV DOTNET_ROOT="/usr/bin/dotnet"
ENV PATH="$PATH:/usr/bin/dotnet"
RUN echo "export PATH=$PATH:/usr/bin/dotnet" >> ~/.bashrc

# Install python
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.9 python3.9-distutils python3.9-dev

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

WORKDIR /app/wrapper
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
RUN python3.9 get-pip.py
RUN pip install -r req

EXPOSE 8080

CMD ["python3.9", "server.py"]
