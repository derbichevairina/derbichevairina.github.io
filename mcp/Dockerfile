FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.12 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY booking_mcp ./booking_mcp
CMD [".venv/bin/python", "-m", "booking_mcp"]
