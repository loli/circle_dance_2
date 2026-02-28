This is a classic "feature extraction" challenge in Music Information Retrieval (MIR). Electronic music is particularly tricky because, unlike acoustic instruments, the sounds are often engineered to fill the entire frequency spectrum or use heavy compression that levels out the dynamics you'd normally use for detection.

To handle the "sustained" vs. "transient" (sudden) elements, you essentially need to split your processing pipeline into two tracks.

1. The Harmonic-Percussive Source Separation (HPSS)

The most effective first step is to treat the audio stream with HPSS. This algorithm decomposes an audio signal into two distinct components:

    The Harmonic Component: Long, horizontal structures in a spectrogram (the basslines, pads, and leads).

    The Percussive Component: Vertical "spikes" in a spectrogram (the kicks, hats, and snares).

By running your Chroma extraction only on the Harmonic component, you filter out the "noise" of the drums that might be triggering false note detections. Conversely, you can use the Percussive component to trigger your visual "explosions" or rhythmic pulses.

2. Adaptive Thresholding & Temporal Windows

Since you mentioned thresholding by "general recent average loudness," you’re already on the right track, but you can refine how you apply it to different frequency bands:
For Continuous Elements (The "Drones")

For things like that continuous bass note, you aren't looking for an Attack; you're looking for Energy Stability.

    Approach: Use a longer integration window. If a specific frequency bin stays above a certain threshold for, say, 200ms without dropping, you classify it as a "State" rather than an "Event."

    Visualization Tip: These elements are best represented by evolving shapes, color shifts, or flowing lines rather than sudden flashes.

For Sudden Elements (The "Transients")

High hats and snares have a massive amount of energy in a very short time, often across high frequencies.

    Approach: Use Spectral Flux. This measures how quickly the power spectrum changes from one frame to the next. A massive spike in flux—even if the total volume is lower than the bass—indicates a transient.

    Visualization Tip: Use these to trigger high-frequency "particles" or sharp geometric scaling.

3. The "Spectral Centroid" as a Proxy

If you want to distinguish between a "heavy" synth and a "piercing" lead without complex note decoding, look at the Spectral Centroid.

Think of this as the "center of mass" of the sound.

    Low Centroid: The sound is bass-heavy. Even if it's loud, it feels "dark."

    High Centroid: The sound is bright or "tinny."

By mapping the Centroid to your visualizer's color palette (e.g., Low = Deep Blues/Reds, High = Neon Whites/Yellows), the visualization will intuitively "feel" like the music even if the note extraction isn't 100% perfect.

4. Multi-Band Enveloping

Instead of one global average loudness, split your stream into three bands: Low, Mid, and High.

    Low (0-150Hz): Use this to drive the "physics" of your visualization (gravity, scale, or vibration).

    Mid (150Hz-4kHz): Use your ChromaQT data here. This is where the melodic information lives.

    High (4kHz+): Use this for "texture" and "sparkle" in the visuals.

By separating the "thump" of the kick (Low) from the "shimmer" of the hat (High), you avoid the visual "jitter" that happens when a loud bass note accidentally triggers a high-frequency visual effect.