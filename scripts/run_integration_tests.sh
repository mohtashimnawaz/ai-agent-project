#!/usr/bin/env bash
set -euo pipefail

if [ -z "${TAVILY_API_KEY:-}" ]; then
  echo "TAVILY_API_KEY not set; aborting integration tests"
  exit 1
fi

if [ -z "${TAVILY_REDIS_CACHE_URL:-}" ]; then
  echo "TAVILY_REDIS_CACHE_URL not set; aborting integration tests"
  exit 1
fi

python -m pytest -q -m integration
