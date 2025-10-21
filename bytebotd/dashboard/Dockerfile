FROM python:3.13-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y bash curl docker-cli && rm -rf /var/lib/apt/lists/*

# --- Install Python dependencies ---
# Install dependencies directly (requirements.txt is in the source)
RUN pip install --no-cache-dir websockets psutil prometheus-client

# copy Bytebot source
COPY . /app

EXPOSE 9993 9994

CMD ["python3", "dashboard/server.py"]