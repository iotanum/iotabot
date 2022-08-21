FROM ubuntu as base

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

RUN apt-get -y update && apt-get install -y wget

# Install dotnet
RUN wget https://download.visualstudio.microsoft.com/download/pr/0c66ddb7-c3c3-4814-9092-fcc2816cc7f6/2a7988ffe2cca87fc011778bf1d1c684/dotnet-sdk-6.0.400-linux-musl-arm.tar.gz
RUN mkdir -p $HOME/dotnet && tar zxf dotnet-sdk-6.0.400-linux-musl-arm.tar.gz -C $HOME/dotnet
RUN echo "DOTNET_ROOT=$HOME/dotnet" >> ~/.bashrc
RUN echo "PATH=$PATH:$HOME/dotnet" >> ~/.bash_profile

# Install python
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.9

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
