
Rough first approach:

Since you are on Ubuntu without a GPU, we will focus on a Spectral Peak Picking approach. This method converts audio into the frequency domain using a Fast Fourier Transform (FFT) and then identifies the strongest frequency components.

To make this work for polyphony, we will use NumPy to perform the FFT and SciPy to find peaks in the resulting spectrum.
1. The Strategy

Instead of looking for a single pitch, we will:

    Capture a window of audio.

    Apply a Hanning Window (to reduce "leakage" at the edges of the buffer).

    Perform an FFT to get the magnitude spectrum.

    Apply a Peak Finder to identify multiple dominant frequencies.

    Convert those frequencies to MIDI note names.

----

Updated Implementation with HPS

The Harmonic Problem: If you play a middle C, this script will likely show C4, C5, and G5. This is because the FFT sees the overtones.

Adding Harmonic Product Spectrum (HPS) is the classic "non-AI" way to solve the polyphony problem.

The core idea is clever: because a musical note consists of a fundamental frequency (f0​) and integer multiples (harmonics) like 2f0​,3f0​,4f0​, we can "compress" the spectrum. By downsampling the FFT data and multiplying it by the original, the harmonics align with the fundamental. The "true" notes get amplified, while the "ghost" overtones cancel each other out.
