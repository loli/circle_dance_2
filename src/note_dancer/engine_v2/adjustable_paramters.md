Here is a breakdown of the four control parameters. These act as the "sensitivity knobs" for your visualizer, allowing you to calibrate the analyzer to the specific mix and energy of different tracks.

### Parameter Reference Guide

| Parameter | Purpose | Sensible Range | Max Range |
| --- | --- | --- | --- |
| **`low_gain`** | Multiplier for the Bass (Sub/Kick) envelope. | 5.0 — 20.0 | 0.0 — 100.0 |
| **`mid_gain`** | Multiplier for the Mid-range (Vocals/Lead synths). | 5.0 — 20.0 | 0.0 — 100.0 |
| **`high_gain`** | Multiplier for the High-range (Hats/Snare snaps). | 5.0 — 20.0 | 0.0 — 100.0 |
| **`flux_sens`** | Sensitivity for transient "hit" detection. | 0.5 — 2.0 | 0.0 — 10.0 |
| **`norm_mode`** | Note normalization mode: `fixed `, `competitive` or `statistical` | - | - |

---

### Detailed Descriptions


#### 1-3. The Gain Multipliers (`low_gain`, `mid_gain`, `high_gain`)

* **What they do:** These scale the raw Root-Mean-Square (RMS) amplitude of their respective frequency bands. Since electronic music is often heavily compressed, the raw RMS values are usually small decimals (e.g., ). The gain boosts these into a usable  range for your visualizer.
* **When to adjust:** If your visuals feel "static" or barely moving, increase the gain. If the visuals are "maxed out" (stuck at 1.0) despite a quiet section, decrease it.
* **Max Range Note:** Setting these to `0.0` effectively mutes that visual channel. Going above `50.0` will likely result in "clipping," where the visual stays at its maximum size constantly.
* **Auto-gain:** The RMS are also subject to an auto gain element, adapting them depending on the current songs maximum recent energy in the band.


#### 4. Flux Sensitivity (`flux_sens`)

* **What it does:** This is the threshold for detecting "impacts." It multiplies the Spectral Flux result before it's sent.
* **When to adjust:**
    * **Increase** if the music has a lot of subtle percussion (like minimal techno) that isn't triggering your visual "explosions."
    * **Decrease** if the song is very "busy" (like Breakcore) and the visuals are flickering too rapidly to see clearly.
* **Max Range Note:** A value of `0.0` disables all transient-based visual triggers. High values (above `5.0`) will cause almost every tiny change in the audio to be registered as a "massive hit."


#### 4. Note normalization (`norm_mode`)

* **What it does:** Determines how note energies are processed and normalized. Effects which notes pass through and their energy values.
* **`fixed`**: This variant treats your visualizer like a physical VU meter. It ignores the "history" of the song and maps raw audio energy directly to a fixed visual range based on human hearing thresholds.
* **`competitive`**: This variant normalizes note energies based on the strongest notes in the current frame. It creates a "spotlight" effect where only the most prominent notes are highlighted.
* **`statistical`**: This variant is the "intelligent" approach. It uses the long-term history of the song to create a stable, human-centric visual scale that adapts to the overall loudness of the set.
