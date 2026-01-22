FROM python:3.11-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy bindings
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system . --extra dev

# Copy output
COPY . .

# Run the application
CMD ["python", "main.py"]
