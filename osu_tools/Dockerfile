FROM ubuntu as base

WORKDIR /app

# Pull osu pp-calc stuff
RUN apt-get update -y && apt-get install git -y
RUN git clone --depth 1 https://github.com/ppy/osu-tools.git
RUN git clone --depth 1 https://github.com/ppy/osu.git

# Hacky tiem
# Pull only the ruleset dirs from main osu repo and branch
# TODO it's not working atm? Broken master
#COPY set_and_pull_rulesets.sh .
#RUN ./set_and_pull_rulesets.sh

FROM bitnami/dotnet-sdk:6 as final

# Install python
RUN apt-get -y update && apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.9 python3.9-dev python3.9-venv

WORKDIR /app
RUN mkdir osu-tools
RUN mkdir osu
RUN mkdir wrapper

COPY --from=base /app/osu-tools /app/osu-tools
# TODO
COPY --from=base /app/osu /app/osu
COPY wrapper /app/wrapper

# TODO not working rn, broken master
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
