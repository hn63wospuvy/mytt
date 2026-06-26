# Backend image for the CLOUD profile. One image, two roles (the compose file
# picks the role via `command`): the LiveKit agent worker and the token server.
# The cloud deployment is stateless (no login, no DB). The cloud profile needs
# NO on-device model runtimes — Gemini Live does STT+LLM+TTS server-side — so we
# install only [livekit,http,cloud] (no mlx / whisper). Build context is the repo
# root (see docker-compose.yml).

# --- Stage 1: build the React/Vite web client (frontend/dist) -----------------
# The token server serves this built client. We build it here rather than ship a
# host build (frontend/dist is dockerignored). WORKDIR /frontend so the produced
# dist is unambiguously /frontend/dist for the runtime COPY --from=build below.
FROM node:20-slim AS build
WORKDIR /frontend
COPY frontend/ .
RUN npm ci && npm run build

# --- Stage 2: the Python runtime image ---------------------------------------
FROM python:3.12-slim

# av / onnxruntime ship manylinux wheels; build-essential is a safety net for
# any sdist-only transitive dependency. Remove it if your dep set is all-wheel.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Copy the backend tree. The runtime image flattens backend/ into /app, so
# server.py sits at /app/src/tutor_agent/token_server/server.py and its
# parents[4] is the filesystem root, NOT the repo root — so the WEB_DIR default
# does not survive the container. We instead copy the built web client to
# /app/frontend/dist and point the token server at it via ENV WEB_DIR below.
# PYTHONPATH=/app/src makes this source tree shadow the pip-installed package
# copy.
COPY backend/ /app/

# Built web client from the node stage. The token server serves /app/frontend/dist
# (see ENV WEB_DIR). Owned by root here; the `app` user (created below) only needs
# read access, which the default perms allow.
COPY --from=build /frontend/dist /app/frontend/dist
ENV WEB_DIR=/app/frontend/dist

RUN pip install ".[livekit,http,cloud]"

# Pre-cache any plugin assets (VAD / turn-detector) the agent imports at module
# load. The cloud profile doesn't use them at runtime; `|| true` keeps the build
# green if there's nothing to fetch.
RUN python -m tutor_agent.agent download-files || true

# Drop root.
RUN useradd --create-home app && chown -R app /app
USER app

# token server :8080 (also serves the web client).
EXPOSE 8080
