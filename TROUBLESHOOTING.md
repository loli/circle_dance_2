# Troubleshooting

## No Audio Input Detected

**Problem:** Engine runs but shows no audio levels or activity.

**Solutions:**
- Check that your microphone or audio device is actually producing sound
- Use `pavucontrol` to verify the correct input device is selected
- Ensure your audio device permissions are correct: `pacmd list-sources | grep -A 2 "name:"`

## Can't Visualize System Audio (Spotify, YouTube, etc.)

**Problem:** Only picks up microphone, not system audio.

**Steps:**
1. Start the engine: `uv run audio-engine`
2. Open `pavucontrol` in another terminal
3. Go to the **Recording** tab
4. Find the Python process and select **Monitor of [Your Device]** from the dropdown
5. Start the visualizer

**Note:** Music must be actively playing for the "Monitor" option to appear.

## Audio Levels Are Flat or Unresponsive

**Problem:** Audio input detected but no visual response.

**Causes & Fixes:**
- **Wrong device monitored:** Use `pavucontrol` to select the correct **Monitor** device (not the microphone itself if using system audio)
- **Audio locked by another app:** Close exclusive audio applications (DAWs, other audio software)
- **Low gain:** Check `pavucontrol` > Input Devices and set gain to 0dB

## Visualization Stutters or Lags

**Problem:** Audio analysis works but visuals are choppy.

**Solutions:**
- **Increase latency buffer** (helps stability but adds lag):
  ```bash
  PULSE_LATENCY_MSEC=42 ./run.sh
  ```
  Start with 42ms (two chunks). Increase to 60-80ms if still stuttering.

- **Reduce CPU load:** Close other applications, disable desktop effects

- **Check for Xruns** (buffer underruns): If you see "Input Overflow" errors in console, buffer is too tight—increase `PULSE_LATENCY_MSEC`

## Connection Refused or Engine Not Found

**Problem:** Visualizer can't connect to engine.

**Fixes:**
- Ensure engine is running first: `uv run audio-engine` in one terminal
- Wait 1-2 seconds before starting visualizer (engine needs to initialize)
- Check that port 5005 is available: `lsof -i :5005`

## Poor Performance with External Soundcard

**Problem:** Behringer or similar USB soundcards cause pops/clicks.

**Steps:**
1. Set soundcard input gain to 0dB in `pavucontrol`
2. Run with: `PULSE_LATENCY_MSEC=20 ./run.sh`
3. If still problematic, increase to 42ms

See `README_legacy.md` for external soundcard details.

## Missing Dependencies

**Problem:** `ModuleNotFoundError` or import errors.

**Fix:**
```bash
uv sync
```

This installs all required Python packages.
