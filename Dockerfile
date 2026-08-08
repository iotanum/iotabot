FROM python:3.11.0-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /bin/uv

WORKDIR /iotabot

# some performance improvements for UV
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# install deps
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev


FROM python:3.11.0-slim

WORKDIR /iotabot

COPY --from=build /iotabot/.venv /iotabot/.venv
COPY . .

# dont need to run uv run when adding this
ENV PATH="/iotabot/.venv/bin:$PATH"
