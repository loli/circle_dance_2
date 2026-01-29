This summary serves as the "Technical Manual" for your visualizer. It defines how the raw audio mathematics map to visual behavior.

### 📋 Audio Analysis Feature Map

The analyzer transmits a **76-byte binary packet** containing 19 floating-point numbers.

---

### 1. Dynamics & Energy

These features track the volume and "pressure" of the music across different frequency ranges.

| Feature | Description | Typical Range | Max Range | Visual Use Case |
| --- | --- | --- | --- | --- |
| **`low`** | Bass/Sub-bass energy (150Hz and below). | 0.2 – 0.8 | 0.0 – 1.0 | Scaling the size of central objects; driving camera "shakes." |
| **`mid`** | Mid-range energy (Vocals, Leads, Snares). | 0.1 – 0.6 | 0.0 – 1.0 | Driving internal object textures or "organic" movement. |
| **`high`** | High-frequency energy (Cymbals, "Air"). | 0.05 – 0.4 | 0.0 – 1.0 | Sparkles, particle emission rates, or jitter effects. |

---

### 2. Timbre & Texture

These features describe the *quality* of the sound rather than just the volume.

| Feature | Description | Typical Range | Max Range | Visual Use Case |
| --- | --- | --- | --- | --- |
| **`brightness`** | The "Spectral Centroid." Center of mass of the sound. | 0.1 – 0.7 | 0.0 – 1.0 | Shifting the Color Palette (e.g., Low = Blue, High = Red). |
| **`flux`** | "Spectral Flux." Rate of change in the spectrum. | 0.1 – 2.0 | 0.0 – 10.0+ | **Impacts.** Triggering flashes, explosions, or rapid rotations on sharp sounds. |

---

### 3. Rhythm & Timing

These features provide the "grid" for your animation, extracted via the `aubio` tempo engine.

| Feature | Description | Typical Range | Max Range | Visual Use Case |
| --- | --- | --- | --- | --- |
| **`bpm`** | Calculated beats per minute. | 60.0 – 180.0 | 0.0 – 500.0 | Synchronizing constant rotations or swaying motions. |
| **`is_beat`** | Binary trigger (1.0 at the instant of a beat). | 0.0 or 1.0 | 0.0 – 1.0 | Reseting an animation cycle or triggering a logic "Step." |

---

### 4. Harmony & Pitch (`notes`)

This is an array of **12 floats**, each representing a semi-tone in the Western scale (C, C#, D, D#, E, F, F#, G, G#, A, A#, B).

| Feature | Description | Typical Range | Max Range | Visual Use Case |
| --- | --- | --- | --- | --- |
| **`notes[0-11]`** | Harmonic energy for each specific pitch. | 0.0 – 0.6 | 0.0 – 1.0 | Mapping specific notes to 3D positions or lighting specific areas. |

---

### 🛠 Visual Interpretation Strategy

* **The "Kick" logic:** Combine `low` and `is_beat`. If `is_beat` is 1, check `low`. If `low > 0.8`, it's a "Heavy Kick"; trigger a massive visual event.
* **The "Clap" logic:** Watch the `flux`. A sudden jump in `flux` without a corresponding jump in `low` usually indicates a snare, clap, or high-hat.
* **The "Melody" logic:** Use the `notes` array. If `notes[0]` (C) and `notes[7]` (G) are high, the song is playing a perfect fifth. You can use this to generate geometric harmony (like a star with 5 points).

**Would you like to implement the "Lerping" logic now? This will make the `low`, `mid`, and `high` values move smoothly instead of "teleporting" between numbers.**