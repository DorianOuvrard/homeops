FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation.
RUN pip install --no-cache-dir uv

# Copy dependency manifests + source for installation.
COPY pyproject.toml uv.lock ./
COPY bot/ ./bot/

# Install the package and its dependencies into the system Python.
# --no-cache avoids storing the uv cache layer inside the image.
RUN uv pip install --system --no-cache .

CMD ["python", "-m", "bot.main"]
