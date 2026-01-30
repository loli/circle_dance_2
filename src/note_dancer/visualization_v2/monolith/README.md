# The "Kinetic Monolith"

Imagine a single, high-definition 3D cube or pillar floating in a void. This is the ultimate test of your **Weighted Inertia** and **Attack/Decay** settings.

* **The Bass (Heavy Inertia):** The Monolith doesn't just "jump" to the bass; it expands in volume. Because you set a Slow Decay for the Lows, it feels like it’s breathing or under high pressure.
* **The Kicks (Impact):** When the impact event triggers, the Monolith doesn't scale—it jitters. A frame-perfect, high-frequency "shiver" that feels like a physical strike.
* **The Mids/Melody (The Core):** The Active Notes drive the internal glow and color of the Monolith. Using a **Sticky Centroid** logic, the color smoothly glides toward the mathematical center of the current harmony, creating stable "Color Chapters" rather than frantic flickering.
* **The Highs (The Atmosphere):** The Highs drive the "snappy" jitter and high-frequency vibrations of the Monolith edges, making the shape feel electrically charged during intense treble sections.

## Effects of the audio engine settings

* **Attack/Decay Visibility:** Adjust the Low Dcy. You will see the Monolith stay "inflated" longer after a bass hit, looking like it's made of heavy rubber.
* **Flux Gating:** Watch the Monolith "snap" 15 degrees. If it's snapping too often on quiet parts, raise the Flux Thr in the HUD until only the snare hits cause the rotation.
* **Note Sensitivity:** The cube will change color based on active_notes. Use the Note Sens slider to find the "sweet spot" where the **Sticky Centroid** has enough solid data to anchor the color to the song's actual key changes.

### Pro-Tuning Tip

For the most "ideal" experience, try setting a High Low-Attack (fast expansion) and a Very Low Low-Decay (slow contraction). This creates a "Pressure Valve" effect where the music seems to physically pump air into the Monolith.

## Other notable effects

* **BPM Hedging:** The background pulse speed is tied to events["bpm"]. Notice how even on slow songs, the "breathing" remains energetic because of the 90–180 hedging.
* **Circular Hue Drift:** Because the color logic handles the 0.0-1.0 wrap-around, you'll see the Monolith transition naturally through the spectrum (e.g., passing through Purple to get from Blue to Red).
