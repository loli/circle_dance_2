#!/bin/bash
set -euo pipefail

# start engine in background (runs the function directly so it uses the same env)
uv run audio-engine &
ENGINE_PID=$!

# ensure engine is killed on exit/signals
_cleanup() {
  echo "Stopping engine ($ENGINE_PID)..."
  kill -TERM "$ENGINE_PID" 2>/dev/null || true
  wait "$ENGINE_PID" 2>/dev/null || true
}
trap _cleanup INT TERM EXIT

# give the engine a moment to initialize
sleep 1

# run visualizer (foreground)
#uv run receiver
#uv run viz-simple
uv run viz-radar
#uv run viz-monolith

# cleanup will run via trap