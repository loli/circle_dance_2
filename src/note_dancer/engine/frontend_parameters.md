While the **Analyzer** handles the heavy math, the **Frontend** should handle the "aesthetic" interpretation. These frontend parameters don't change the data itself; they change how that data is translated into pixels and motion.

### Frontend Logic Parameters

| Parameter | Description |
| --- | --- |
| **Smoothing (Lerp)** | A 0.0–1.0 factor that determines how fast a visual object "slides" to a new value. Higher values make visuals snappier; lower values make them fluid and "dreamy." |
| **Chroma Threshold** | The minimum value required for a "Note" to be visible. This filters out background harmonic noise so only the dominant musical notes trigger visual changes. |
| **Decay Rate** | How slowly a "Flash" or "Pulse" fades back to black after being triggered by an `is_beat` or `flux` event. Essential for creating a "tail" on rhythmic hits. |
| **Peak Hold** | The amount of time the visualizer stays at its maximum "scale" after a kick drum hits before it begins to shrink again. Prevents visuals from looking too "jittery." |
| **Color Map Shift** | An offset for the `brightness` (Spectral Centroid) mapping. Allows you to manually shift the entire scene's mood from cold (Blues) to hot (Reds) regardless of the track's brightness. |

---

### Why handle these in the Frontend?

By keeping these in your visual engine (Three.js, Unity, etc.), you can change the "vibe" of the visualizer without re-calculating the audio. For example, a **Techno** preset would use **High Smoothing** and **Short Decay**, while an **Ambient** preset would use **Low Smoothing** and **Long Decay**.

**Would you like me to write a quick Python "Remote Control" script so you can test sending these parameter updates to your Analyzer right now?**