#!/usr/bin/env bash
# Runs once, when the dev container is created: tools, dependencies, and a first build of the UI.
set -euo pipefail

# uv, at the version the project is locked with.
pipx install --force uv==0.9.30

# The node_modules volume is created by Docker as root; hand it to the container user.
sudo chown -R "$(id -u):$(id -g)" web/node_modules

# pnpm through corepack, at the version pinned in web/package.json.
corepack enable

uv sync
(cd web && pnpm install --frozen-lockfile && pnpm build)

cat <<'EOF'

Ready. Start the app with:   uv run design-pipeline        (port 8000)
Work on the UI with:         cd web && pnpm dev --host     (port 5173, proxies /api to 8000)
Run the tests with:          uv run pytest
EOF
