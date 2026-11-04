# The design pipeline as one container: the SvelteKit UI built to static files, served by the Python app.
#
#   docker build -t design-pipeline .
#   docker run --rm -p 8000:8000 -v design-pipeline-runs:/data design-pipeline              # offline, scripted model
#   docker run --rm -p 8000:8000 -v design-pipeline-runs:/data \
#     -e PIPELINE_PROVIDER=openai -e PIPELINE_API_KEY=sk-... design-pipeline              # a real model
#
# Then open http://localhost:8000. Runs (generated apps, specs, reviews, timelines) are kept in the /data volume.

ARG PYTHON_VERSION=3.12

# --- 1. The UI ----------------------------------------------------------------------------------------------------
FROM node:24-slim AS ui
RUN corepack enable
WORKDIR /web
COPY web/package.json web/pnpm-lock.yaml web/.npmrc ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build


# --- 2. The Python environment -----------------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS app
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

# Dependencies first, so editing the app does not re-download them.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project

# The app is installed in place (editable): it finds prompts/, skills/, instructions/ and web/build next to it, and
# those Markdown files stay easy to swap with a bind mount (-v ./prompts:/app/prompts) without rebuilding.
COPY designpipeline ./designpipeline
COPY prompts ./prompts
COPY skills ./skills
COPY instructions ./instructions
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev
COPY --from=ui /web/build ./web/build

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --home-dir /home/app --create-home app \
    && mkdir /data && chown app:app /data

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PIPELINE_HOST=0.0.0.0 \
    PIPELINE_PORT=8000 \
    PIPELINE_OUTPUT_ROOT=/data

USER app
VOLUME ["/data"]
EXPOSE 8000
CMD ["design-pipeline"]
