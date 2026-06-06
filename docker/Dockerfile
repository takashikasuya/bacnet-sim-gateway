# Optional distribution (ADR-008: native/ARM is first-class, Docker is optional).
# Multi-arch friendly: python slim builds on arm64/amd64.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv sync --no-dev

COPY config ./config

# BACnet/IP (UDP 47808). Use host networking for discovery (see compose).
EXPOSE 47808/udp
ENTRYPOINT ["uv", "run", "bbc-sim"]
CMD ["run", "--config", "config/simulator.yaml"]
