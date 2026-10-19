#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/.cache/python"
command -v uv >/dev/null || { echo 'Install uv from https://docs.astral.sh/uv/ then rerun this script.'; exit 1; }
uv venv --python 3.11 --allow-existing .venv
# Remove the development-only link to cached packages if one exists.
find .venv -name local-cached-test-deps.pth -delete
if [ ! -f requirements.lock ]; then
  uv pip compile pyproject.toml --extra dev -o requirements.lock
fi
uv pip sync --python .venv/bin/python requirements.lock
uv pip install --python .venv/bin/python --no-deps -e .
if [ ! -f .env ]; then cp .env.example .env; fi
printf '\nSetup installed. Set the model variables in .env, then follow README.md.\n'
