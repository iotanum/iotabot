# Use a lightweight ARM-compatible base image
FROM ubuntu:24.04 AS base

# Set working directory
WORKDIR /app

# Install essential tools and pull osu pp-calc repositories
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    git && update-ca-certificates && \ \
    git clone --depth 1 https://github.com/ppy/osu-tools.git && \
    git clone --depth 1 https://github.com/ppy/osu.git && \
    rm -rf /var/lib/apt/lists/*

# Final stage
FROM ubuntu:24.04 AS final

# Set environment to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update and upgrade essential packages
RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends \
    software-properties-common && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies for .NET 8 and Python 3.13
RUN add-apt-repository ppa:dotnet/backports && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
    dotnet-sdk-8.0 python3.13-full python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Set working directory and prepare application directories
WORKDIR /app
RUN mkdir -p osu-tools osu wrapper

# Copy cloned repositories from the base stage
COPY --from=base /app/osu-tools /app/osu-tools
COPY --from=base /app/osu /app/osu
COPY wrapper /app/wrapper

# Build osu-tools
WORKDIR /app/osu-tools
RUN ./UseLocalOsu.sh && \
    dotnet restore && \
    dotnet publish -c Release -r linux-arm64 --self-contained -p:PublishReadyToRun=true -o /app/osu-tools/publish

# Install Python dependencies
WORKDIR /app/wrapper
RUN python3.13 -m pip install --no-cache-dir --upgrade pip && \
    python3.13 -m pip install --no-cache-dir -r req

# Reduce image size by removing unnecessary files
RUN apt-get remove -y software-properties-common && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Expose port for the Python server
EXPOSE 8080

# Default command to run the Python server
CMD ["python3.13", "-u", "server.py"]
