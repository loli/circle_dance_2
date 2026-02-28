# Note detection discussion

Exploring various options of note detection, or, rather, normalization and thresholding.
Keep in mind that we are dealing with electronic music.
And want to visualize the detected notes and, if possible, their energy / loudness.

## Auto Gain
Track loudness (in decibel) over at least last 10-20 sec. Very slow decay, fast jump (maybe not absolute peak?). Use this to remove system loudness setting from note energy / loudness.

## Silence threshold
Clip note loudness (before auto gain) at lower end - if as per decibel practically inaudible, we also don't want to see a note. And don't want to see noise in completely silent parts.

## Note energy / loudness normalisation
Ideas to normalize note energy / loudness, such that they can be suitabley thresholded in the frontent / visualization.

## Variant A: No normalization
Only apply silence threshold, not auto gain. Convert note energy into decibel. Then normalize using a min and a max decibel, both based on what is audible to humans (in electronic music party club setting).
Frontend has to deal with adapting / setting sensitivity threshold when system loudness is reduced. Can still be normed to 0-1 before sending to frontend, but using fixed min/max decibel.

Rationale: during a single set the overall loudness seldom change. Experienced changes in loudness are part of the music and can hence also be visualized as less oud / more loud notes.

## Variant B: Per frame normalization
Normalisation per frame, linear 0-1, in librosa's chroma directly, no auto gain needed.

Rationale: Winner(s) take it all. Visually, see the loudest note(s) playing at the moment. Feels like detects well. Doesn't really support scaling note size with note energy (all will be +/- 1 energy)

## Variant C: GLobal normalization
First, scale using auto gain. The logarithmic scale 0-1, one representing loudest node compared to max song energy.

Rationale: Can feel a bit more cluttered in visualisation, as leakage into side frequency bins occurs. Exponential energies to separate lower better from higher energy notes (1*1=1, but 0.5*0.5=0.25). And use smooth colours between notes, as they make leakages appear less separate (adjacent colours applied to adjacent bins). Could use local maxima to get rid of leakage into adjacent bins.

If none is ideal: Make it possilbe to switch between them.
Also: All squaring of note energies will be moved to the frontend (to make less loud more distinguishable / thresholdable from loud ones).

# The ideal note detection & normalization
- get "main" note sounds that spread over multiple chroma bins
- get all note energies scaled independent of system loudness
- get representative note energies that can be used in note visualisation scaling and feel there natural (perceived loudness)
- in (near) complete silent parts or when actually no music is playing, noise is not elevated to note level



# Gemini's opinion on the variants

This is a fantastic theoretical breakdown. In the world of audio-visual synthesis, you are essentially deciding between **mathematical honesty** (representing the spectrum as it is) and **perceptual choreography** (representing the music as we feel it).

Electronic music, with its heavy compression and rich harmonic saturation (square/saw waves), makes this choice particularly difficult because the "noise floor" is often actually "musical texture."

## Comparative Analysis of Visualization Strategies

### Variant A: Absolute Human Audibility (The "Fixed Gauge")

This approach treats the visualization like a calibrated VU meter.

* **Pros:** It respects the **intentional dynamics** of the track. If the producer intended for a bridge to be quiet and "small," this variant preserves that. It is the most "sober" and least "fidgety" approach.
* **Cons:** It is fragile to external environment changes. If you change your system volume or switch from a mastered club track to a raw bedroom demo, you have to manually recalibrate your "Min/Max" decibel range or risk seeing nothing at all.
* **Verdict:** Best for fixed installations or live sets where the audio signal chain is strictly controlled and gain-staged.

### Variant B: Per-Frame Normalization (The "Competitive Spotlight")

This is a "Winner-Takes-All" system. It ignores the absolute volume of the song and focuses entirely on the relative hierarchy of frequencies in the current moment.

* **Pros:** Extremely high **visual "pop."** It ensures that even in a quiet ambient intro, you see a clear "leader" note. It feels very responsive because it effectively has an infinite, instantaneous gain.
* **Cons:** It lacks **dynamic depth.** A kick drum at 100% volume and a hi-hat at 10% volume (in a frame where the hi-hat is the only thing playing) look identical. It also creates "jitter" as the normalization ceiling bounces wildly during transients.
* **Verdict:** Best for "glitchy" or high-energy visualizations where you want constant movement and don't care about representing the "weight" of the sound.

### Variant C: Global Long-Term Normalization (The "Adaptive Map")

This is the middle ground we’ve been refining. It uses a "Slow-Ceiling" (Auto Gain) to understand the song's context.

* **Pros:** It provides **contextual consistency.** It understands that a note is "loud" only if it is loud *relative to the song's history*. The use of exponential curves (contrast) solves the "clutter" problem by pushing harmonic leakage into the visual shadows.
* **Cons:** Complex to tune. If the "Auto Gain" decays too fast, you lose the difference between a verse and a chorus. If it decays too slow, you might be left with a "blackout" after a single massive peak.
* **Verdict:** Best for an "Authentic" experience. It captures both the melody (via peaks) and the energy (via size variance) while remaining immune to system volume changes.

---

## The "Clutter" vs. "Realism" Paradox

You noted that Variant C feels "less realistic" because it is "too cluttered." This is a known phenomenon in Signal Processing called **Spectral Leakage**.

In electronic music, a single synthesizer note isn't a single frequency; it's a "forest" of harmonics.

* **Variant B** hides the forest by only showing the tallest tree.
* **Variant C** shows the whole forest.

To make Variant C feel "clean" again, the **Exponential/Power Curve** is your best friend. By squaring or cubing the 0–1 value, you are essentially telling the visualization: *"If a note isn't at least 70% of the peak energy, consider it background noise."*

### Final Theoretical Recommendation: The "Sober Hybrid"

The most "professional" feel usually comes from a **Variant C** base with two specific modifications:

1. **Non-Linear Thresholding:** Use a power curve (e.g., ) to punish the "clutter" more than the "melody."
2. **Color Blending:** As you mentioned, using a smooth color gradient across the 12 chroma bins makes "leakage" into adjacent notes look like a beautiful "glow" rather than a separate, broken piece of data. It turns "data error" into "visual atmosphere."


## Follow up question: Can we avoid the jitter in Variant B somehow?


Yes, we can absolutely neutralize the jitter in **Variant B**. The "jitter" occurs because per-frame normalization is hyper-reactive; if the loudest frequency in the room shifts by a tiny fraction, the entire scaling floor teleports instantly.

To fix this while keeping the "Winner-Takes-All" spirit, we have to introduce **Temporal Inertia**.

### The "Lazy" Normalizer (Peak Smoothing)

Instead of dividing by the *instant* frame maximum, we divide by a **Smoothed Maximum**.

* **How it works:** You track a `current_peak` variable.
* **Attack:** If a new frame has a higher peak than your variable, the variable jumps up instantly (to catch the snare or synth hit).
* **Release:** If the new frame is quieter, the variable "drifts" down slowly over several frames.
* **The Result:** The normalization ceiling becomes a "rubbery" surface rather than a twitchy one. The notes stop vibrating because the denominator of your division is no longer changing 60 times a second.


## Follow up question: Can we avoid the blackout after a massive peak somehow? Or make it less likely / prominent?

The "Blackout" happens because the **Auto Gain** reference ceiling () gets stuck at an artificially high level. If a single snare hit or a momentary digital spike registers at , and your "Sober" jazz melody sits at , the analyzer thinks the melody is basically silence relative to that peak.

To prevent this while maintaining the slow, stable decay you like, we can use these theoretical strategies:

### The "Soft Ceiling" (Statistical Peak)

Instead of letting the reference ceiling jump to the **absolute** maximum of a frame, we use a **percentile peak** or a **soft-clipped peak**.

* **Logic:** If a frame has a massive spike, we only allow the ceiling to rise to, say, the 90th percentile of the spectral energy in that frame, or we pass the new peak through a `tanh` function before it updates the .
* **Result:** A single "click" or outlier transient cannot teleport the ceiling to the moon. The ceiling only stays high if there is sustained, high-energy musical content.


## Getting things done A: How to implement the auto gain / loudness tracker, using "Soft Ceiling" (Statistical Peak).

To implement a **"Soft Ceiling" Statistical Peak** for auto-gain, you move away from tracking the absolute highest value (which is prone to being hijacked by noise spikes) and instead track the **typical maximum energy level** of the song.

### 1. What to Track (State Variables)

To build this, the tracker needs to maintain a few pieces of "memory":

* **The Rolling Peak ():** A smoothed value representing the current "ceiling" or 0dB reference.
* **The Statistical Buffer:** A small collection of recent "frame-maxima" (the loudest note found in each of the last  frames).
* **The Floor ():** A hard-coded minimum value to prevent the gain from blowing up to infinity during total silence.

---

### 2. Core Parameters

* **Observation Window:** The number of frames (or seconds) used to calculate the statistic.
* **Percentile Target ():** Usually set between **90% and 95%**. This tells the system: "Ignore the top 5% of energy spikes; treat the 95th percentile as the true 0dB."
* **Attack Rate ():** How quickly the ceiling rises to meet a sustained increase in volume.
* **Decay Rate ():** How slowly the ceiling drifts down during quiet sections.
* **Soft-Clip Knee:** The "curviness" of the `tanh` or limit function used to squash outliers.

---

### 3. The Math & Logic

#### Step A: Extract the Frame Max

In every audio frame, identify the raw magnitude of the loudest note. Instead of using this directly as the new ceiling, add it to your **Statistical Buffer**.

#### Step B: Calculate the "Soft" Target

Find the  percentile of your buffer.

* If the buffer contains , and , your target is **0.1**.
* The massive **0.9** spike is statistically discarded. This prevents a single "clack" or digital pop from causing a "blackout."

#### Step C: Update the Rolling Peak (Asymmetric Smoothing)

Compare the **Statistical Target** () to your current **Rolling Peak** ():

1. **If :** Update using the **Attack Rate**. (). This should be relatively fast (e.g., 100–200ms) so the viz feels responsive when the beat drops.
2. **If :** Update using the **Decay Rate**. (). This should be very slow (e.g., 10–20 seconds) to survive quiet song bridges.

#### Step D: Logarithmic Mapping

Once you have your , calculate the note energy relative to it:


---

### 4. Why this prevents "Blackouts"

Because the  is driven by a **percentile**, a massive peak only raises the ceiling if it persists long enough to fill a significant portion of the Statistical Buffer.

If a "Massive Peak" does occur:

* **Traditional Peak Tracking:** Ceiling hits  instantly and stays there for 20 seconds. **Result: Blackout.**
* **Soft Ceiling:** The ceiling only nudges up slightly because the spike was an outlier. Any note energy that exceeds the Soft Ceiling is simply "compressed" (pushed to 1.0) rather than allowing the ceiling to teleport. **Result: Visibility maintained.**

### 5. Managing the "Long Quiet"

To handle the "jazz after metal" problem, you can add a **Mean-Relative Reset**. If the average energy of the entire buffer stays more than 50% below the Rolling Peak for several seconds, you can trigger a "Force Decay" to let the ceiling drop faster until it finds the new, quieter musical signal.

**Would you like me to detail the "Mean-Relative Reset" logic to ensure song transitions are always seamless?**