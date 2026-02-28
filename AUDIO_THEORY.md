# Audio & Physical Theory

## Why This Approach?

Note Dancer analyzes music like a musician would: breaking it down into **rhythm, pitch, and texture**. Rather than raw waveforms, we extract musically meaningful features that align with how humans actually perceive sound.

## The Frequency Spectrum & Why We Split It

Human hearing spans roughly 20 Hz to 20 kHz. Different frequency ranges carry different musical meaning:

### Low Frequencies (< 150 Hz): The Bass
- **Physical:** Large wavelengths (17 meters at 20 Hz), felt more than heard
- **Musical Role:** Provides weight, foundation, groove
- **Perception:** Not precise pitch—we feel *energy* and *tension*
- **Decay:** Slow (0.1-0.2s). Bass pads and kick drums resonate; they don't snap off immediately
- **Why it matters:** Electronic music is built on bass. A silent bass track means no groove, even if melody is playing

### Mid Frequencies (150-4000 Hz): Vocals & Melody
- **Physical:** Sweet spot for human speech and hearing sensitivity
- **Musical Role:** Carries melody, chords, human emotion
- **Precision:** We can distinctly hear individual notes and timbres here
- **Decay:** Medium (0.05-0.2s). Strings and pianos ring; synthesizers decay programmed
- **Why it matters:** The "hook" of most music lives here

### High Frequencies (> 4000 Hz): Detail & Texture
- **Physical:** Small wavelengths (8.5 cm at 4 kHz), sharp and directional
- **Musical Role:** Sparkle, presence, attack detail, drums, cymbals
- **Perception:** Quick and percussive—we detect changes instantly
- **Decay:** Fast (0.05-0.1s). Cymbals ring briefly; hi-hats snap
- **Why it matters:** Gives "airiness" and presence to a mix; absence = dull, dead sound

## Beat Detection: Rhythmic Anchor

### Physical Principle: Onset Detection
A **beat** is a sudden energy change—typically a drum hit or bass note attack. Mathematically, this is a *transient*: a rapid rise in amplitude.

### Our Approach: Aubio Tempo Detection
Rather than looking for peaks in a single frequency, Aubio scans the entire spectrum for sudden energy spikes. This works because:
- Kicked drums have energy across many frequencies simultaneously
- A single frequency can trick you (a cymbal shimmer might be louder than a kick)
- Real beats happen in *multiple* bands at once

### Why Tempo Matters
Electronic music is *tempo-locked*. The visual animation can sync to BPM, creating physical alignment between music and graphics. Users intuitively expect visuals to "breathe" at the song's tempo.

## Pitch: The 12-Semitone Chromatic Scale

### The Physics of Pitch
A note is a periodic vibration. Two notes an octave apart have a 2:1 frequency ratio:
- A₂ = 110 Hz
- A₃ = 220 Hz
- A₄ = 440 Hz

Western music divides each octave into **12 semitones** (equal temperament). Each semitone is a 2^(1/12) ratio ≈ 1.059× frequency.

### Why 12 Notes?
Historically, 12 is the closest divisor of 2 that feels consonant to human ears. Musically:
- Interval ratios feel "right" (perfect fifth = 7/12 octave)
- Enharmonic equivalence: C# and Db are the same pitch
- Every major key has the same interval pattern: W-W-H-W-W-W-H

### Chroma vs. Frequency
Traditional spectrograms show frequency bins (4000 Hz, 4043 Hz, 4086 Hz...). Instead, we use **chroma**:
- Fold all frequencies into a single octave (20 Hz ~ 40 Hz ~ 80 Hz → all "C")
- This gives us 12 energy values: one per semitone class
- A C major chord (C-E-G at any octave) activates 3 specific chroma bins simultaneously

### Why Chroma for Electronic Music?
- Synthesizers often play octaves (C2 + C3 + C4 simultaneously)
- Chroma collapses these into a single feature: "C is active"
- **Result:** The visualization responds to the *harmonic content*, not the register (octave)
- Bonus: Computationally lighter than per-frequency tracking

## Transients & Attack Detection

### Physical Definition
A **transient** is an abrupt change in sound—the *attack phase* of a note. Examples:
- The pick hitting a string
- A drum beater striking the head
- A synth envelope opening instantly

### Musical Significance
Humans identify most sounds by their opening milliseconds. A piano with truncated attack sounds synthetic; a drum without punch feels timid.

### Our Approach: Percussive Separation
We use **HPSS** (Harmonic-Percussive Source Separation):
1. Compute short-term spectral changes (vertical axis = percussive)
2. Compute long-term spectral changes (horizontal axis = harmonic)
3. Separate into two components

**Result:** Clean transient detection without sustained notes interfering.

### Flux: Normalized Transient Strength
Raw transient energy varies wildly with mix level. Instead, we compute **flux** as:
```
Recent Flux = (Current Transient Energy) / (Average of Last 20 Frames)
```

This auto-adapts: quieter music still triggers visuals proportionally.

## Loudness & Adaptive Normalization

### The Problem: Dynamic Range
A music mix has extreme dynamics:
- Quiet: -20 dB (synth pad)
- Loud: 0 dB (kick drum, vocal peak)
- **Ratio:** 100:1 in amplitude

Visual systems need [0, 1] mapping. A fixed scale fails:
- Too sensitive: quiet sections are invisible
- Too insensitive: loud sections clip

### Human Loudness Perception
Our ears don't perceive volume linearly. A doubling of perceived loudness is ~10 dB, not proportional to energy. This is why:
- Music sounds bad at very low volumes (we lose bass perception)
- Mixing at moderate levels is easier than at loud levels
- Compression (reducing dynamic range) is ubiquitous in music

### AutoGain Solution
Instead of a fixed scale, we use a **percentile-based peak tracker**:

1. **Track recent peaks** (last 15-20 seconds)
2. **Target the 90th percentile** of peaks
3. **Decay slowly** when peaks drop (slow fade, no sudden collapse)
4. **Attack quickly** when peaks rise (snap to new ceiling)

**Result:** Visual "ceiling" adapts to the mix, but doesn't jitter frame-to-frame. A quiet breakdown stays readable; a sudden drop stays responsive.

### Three Normalization Modes

| Mode | Behavior | Best For |
|------|----------|----------|
| **Statistical** | Per-band AutoGain, decays over song | General electronic/pop |
| **Competitive** | Brightest note is 1.0, others scale around it | Melodic focus, chords |
| **Fixed Scale** | Absolute dB mapping [-40, 0] → [0, 1] | Multi-track mixing, consistent across songs |

## Spectral Centroid: The "Brightness" Feature

### Definition
The weighted average frequency of the spectrum. If energy is concentrated at low frequencies, centroid is low ("dark"). High frequencies make it "bright".

### Formula
```
Centroid = Σ(frequency × magnitude) / Σ(magnitude)
```

### Why It Works
Musically, brightness correlates with:
- **Timbre:** A bright lead synth vs. a dark pad
- **Presence:** Mixing EQ that boosts 5-10 kHz makes mixes pop
- **Emotion:** Bright music feels alert, dark music feels somber

### Electronic Music Context
Producers often sweep filters or use modulation on brightness. A rising centroid is viscerally "opening up"; a falling centroid is "closing down".

## Attack & Decay: Musical Time Constants

### Physics Background
When you pluck a string, the amplitude trace looks like:
```
  ^
  |      Attack  Hold  Decay
  |\______         |\
  |       |_______|  \___
  +--+--+-----------+--+-----
```

Different instruments have different envelopes:
- **Piano:** Loud attack, long decay
- **Kick drum:** Fast attack, medium decay
- **Hat cymbal:** Very fast attack, slow decay (shimmer)
- **Synth pad:** Slow attack, zero decay (sustained)

### Our Attack/Decay Framework
We let users tweak envelope response per band:
- **Low Attack:** How fast bass responds (0.01 = instantaneous, 1.0 = sluggish)
- **Low Decay:** How quickly bass fades (0.01 = immediate, 1.0 = forever)

**Effect:** Lets users simulate physical instruments or design custom "feel".

### Electronic Music Tuning
Default values favor electronic music:
- **Bass:** Slow decay (0.05-0.1) → feels heavy, pressurized
- **Mids:** Medium decay (0.1-0.2) → steady, grounded
- **Highs:** Fast decay (0.4+) → snappy, delicate

## Sample Rate: Why 48 kHz?

### Nyquist Theorem
The maximum frequency you can capture is **half the sample rate**:
- 44.1 kHz → up to 22 kHz (standard music CD)
- 48 kHz → up to 24 kHz (just above human hearing limit ~20 kHz)

### Why Not 96 kHz?
- Only captures 48 kHz (overkill for human hearing)
- Double CPU load, double latency
- No audible difference in analysis accuracy

### Why Not 44.1 kHz?
- Slightly less headroom for high-frequency features
- 48 kHz is the professional standard (video, broadcast)
- Our target devices (Behringer soundcards) default to 48 kHz

## Electronic Music Characteristics

### Tempo-Locked Everything
Unlike acoustic music, electronic music is quantized:
- Drum patterns repeat every 4, 8, or 16 beats
- Synth lines follow grid patterns
- **Design implication:** Visualizations can lock to BPM and feel "locked in"

### Harmonic Simplicity
Electronic drops often use 1-2 chords for 16+ bars:
- A major triad on repeat
- A bass riff that doesn't change
- **Design implication:** Chroma stability is a feature, not noise

### Attack Emphasis
Electronic production emphasizes **punch**:
- Kick drums have aggressive attack
- Bass hits are sudden
- Transient detection is crucial
- **Design implication:** Flux (transient energy) is visually prominent

### Absence of Acoustic Decay
A synthesizer pad doesn't decay naturally—it sustains or stops abruptly:
- No "ring out" unlike piano strings
- Energy levels are more stable
- **Design implication:** AutoGain 15-second half-life works well (no constant tails)

## Summary: Why These Choices

| Feature | Audio Theory Reason |
|---------|-------------------|
| **Force 12-note chroma** | Octave equivalence: C at any octave sounds like the same "pitch class" |
| **Triple-band split** | Human hearing has three perceptual zones; each has different musical role |
| **HPSS decomposition** | Separates "what's playing" (harmonic) from "when it's happening" (percussive) |
| **AutoGain normalization** | Adaptive loudness: ear adjusts to ambient level, so fixed scales fail |
| **Fast attack, slow decay** | Musical time constants: drums snap, pads ring |
| **Aubio for BPM** | Transient detection is the clearest single indicator of rhythm |
| **48 kHz sample rate** | Balances Nyquist margin against latency and CPU load |
| **Percentile-based peak tracking** | Ignores outliers (sudden noise spikes), focuses on mix envelope |
