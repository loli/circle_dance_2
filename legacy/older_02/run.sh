#!/bin/bash

# --- Ubuntu Visualizer Launcher ---


# 2. Start the Audio Engine in the background
echo "Starting Audio Engine..."
uv run python3 audio_engine.py &

# Store the Process ID of the engine so we can kill it later
ENGINE_PID=$!

# 3. Wait a second for the engine to open the stream and socket
sleep 2

# 4. Start the Visualizer
echo "Starting Visualizer..."
uv run python3 live_attack_radar.py

# 5. Cleanup: When the visualizer is closed, kill the background engine
echo "Cleaning up processes..."
kill $ENGINE_PID
echo "Done."