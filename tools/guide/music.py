"""Calm, bright "space" music for the guide video, generated from code (no samples, no
licenses).

Slow pad chords in D major (I – V – IV – ii), a soft sub bass, a gentle rising arpeggio,
bell notes like distant stars and a wash of air, all in a large synthetic hall. The same seed gives the same
music, so every language gets the same soundtrack. The length matches the video.

Usage: python3 tools/guide/music.py <seconds> <out.wav>
"""

from __future__ import annotations

import sys
import wave

import numpy as np
from scipy import signal

RATE = 44_100
CHORD_SECONDS = 8.0
ATTACK = 2.6
RELEASE = 4.0
# The arpeggio steps at 0.42 s: an unhurried pulse of about 71 notes per minute.
STEP = 0.42

# Voicings (Hz) in the middle register. D major: Dmaj9, A6/9, Gmaj9, Em9 (then Dmaj9 again).
NOTE = {
    "A1": 55.00, "B1": 61.74, "D2": 73.42, "E2": 82.41, "G2": 98.00, "A2": 110.00, "B2": 123.47,
    "D3": 146.83, "E3": 164.81, "F#3": 185.00, "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C#4": 277.18, "D4": 293.66, "E4": 329.63, "F#4": 369.99, "G4": 392.00, "A4": 440.00,
    "B4": 493.88, "C#5": 554.37, "D5": 587.33, "E5": 659.25, "F#5": 739.99, "A5": 880.00,
    "B5": 987.77, "C#6": 1108.73, "D6": 1174.66, "E6": 1318.51,
}
CHORDS = [
    {
        "root": "D2",
        "pad": ["D3", "A3", "C#4", "E4", "F#4"],
        "bells": ["F#4", "A4", "C#5", "D5", "E5", "F#5", "A5", "E6"],
    },
    {
        "root": "A1",
        "pad": ["A2", "E3", "F#3", "B3", "C#4"],
        "bells": ["E4", "F#4", "A4", "B4", "C#5", "E5", "F#5", "B5", "C#6"],
    },
    {
        "root": "G2",
        "pad": ["D3", "F#3", "G3", "B3", "D4"],
        "bells": ["G4", "B4", "D5", "F#5", "A5", "B5", "D6"],
    },
    {
        "root": "E2",
        "pad": ["E3", "B3", "D4", "F#4", "G4"],
        "bells": ["E4", "G4", "B4", "D5", "F#5", "B5", "E6"],
    },
]


def envelope(length: int, attack: float, release: float) -> np.ndarray:
    """Raised-cosine attack and release: no clicks, a slow breath in and out."""
    env = np.ones(length)
    a = min(int(attack * RATE), length // 2)
    r = min(int(release * RATE), length - a)
    if a:
        env[:a] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    if r:
        env[-r:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, r))
    return env


def pad_note(freq: float, length: int, rng: np.random.Generator) -> np.ndarray:
    """Three slightly detuned voices of a soft additive tone, spread left, centre, right."""
    t = np.arange(length) / RATE
    out = np.zeros((length, 2))
    for cents, pan in ((-7.0, 0.15), (0.0, 0.5), (6.0, 0.85)):
        f = freq * 2 ** (cents / 1200)
        vibrato = 0.0009 * np.sin(2 * np.pi * rng.uniform(0.08, 0.16) * t + rng.uniform(0, 6.3))
        phase = 2 * np.pi * f * t * (1 + vibrato)
        tone = np.zeros(length)
        for h in range(1, 6):
            tone += np.sin(h * phase + rng.uniform(0, 6.3)) / h**1.35
        out[:, 0] += tone * np.cos(pan * np.pi / 2)
        out[:, 1] += tone * np.sin(pan * np.pi / 2)
    return out / 3


def bell(freq: float, rng: np.random.Generator) -> np.ndarray:
    """A soft FM bell: bright at the strike, fading into a pure tone."""
    length = int(5.5 * RATE)
    t = np.arange(length) / RATE
    index = 1.6 * np.exp(-t / 0.35)
    tone = np.sin(2 * np.pi * freq * t + index * np.sin(2 * np.pi * freq * 2.0 * t))
    amp = (1 - np.exp(-t / 0.004)) * np.exp(-t / 1.7)
    pan = rng.uniform(0.2, 0.8)
    mono = tone * amp
    return np.stack([mono * np.cos(pan * np.pi / 2), mono * np.sin(pan * np.pi / 2)], axis=1)


def pluck(freq: float, pan: float) -> np.ndarray:
    """A soft plucked note: quick but gentle attack, warm decay."""
    length = int(2.6 * RATE)
    t = np.arange(length) / RATE
    tone = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(4 * np.pi * freq * t) * np.exp(-t / 0.25)
    mono = tone * (1 - np.exp(-t / 0.012)) * np.exp(-t / 0.75)
    return np.stack([mono * np.cos(pan * np.pi / 2), mono * np.sin(pan * np.pi / 2)], axis=1)


def hall(seconds: float, rng: np.random.Generator) -> np.ndarray:
    """Impulse response of a large dark hall: decorrelated stereo noise, decaying, darkening."""
    length = int(seconds * RATE)
    t = np.arange(length) / RATE
    noise = rng.standard_normal((length, 2))
    bright = signal.sosfilt(signal.butter(2, 5000, fs=RATE, output="sos"), noise, axis=0)
    dark = signal.sosfilt(signal.butter(2, 1200, fs=RATE, output="sos"), noise, axis=0)
    mix = np.exp(-t / 1.4)[:, None]
    ir = (bright * mix + dark * (1 - mix)) * np.exp(-t / 1.5)[:, None]
    ir[: int(0.025 * RATE)] = 0  # pre-delay
    return ir / np.sqrt(np.sum(ir**2, axis=0, keepdims=True))


def reverb(dry: np.ndarray, ir: np.ndarray) -> np.ndarray:
    wet = np.stack([signal.fftconvolve(dry[:, c], ir[:, c])[: len(dry)] for c in range(2)], axis=1)
    return wet


def render(seconds: float, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    total = int((seconds + 0.5) * RATE)
    pads = np.zeros((total, 2))
    bass = np.zeros((total, 2))
    bells = np.zeros((total, 2))
    arp = np.zeros((total, 2))

    start = -1.5  # the first chord is already sounding when the video starts
    index = 0
    while start < seconds:
        chord = CHORDS[index % len(CHORDS)]
        begin = max(0, int(start * RATE))
        end = min(total, int((start + CHORD_SECONDS + RELEASE) * RATE))
        length = end - begin
        if length > RATE:
            env = envelope(length, ATTACK, RELEASE)[:, None]
            for name in chord["pad"]:
                pads[begin:end] += pad_note(NOTE[name], length, rng) * env * 0.22
            t = np.arange(length) / RATE
            sub = np.sin(2 * np.pi * NOTE[chord["root"]] * t) * envelope(length, 4.0, RELEASE)
            bass[begin:end] += np.stack([sub, sub], axis=1) * 0.09
            # Sparse stars: a few bells per chord, never two at once.
            moment = start + rng.uniform(1.0, 2.5)
            while moment < start + CHORD_SECONDS - 1.0:
                at = int(moment * RATE)
                if 0 <= at < total:
                    note = bell(NOTE[rng.choice(chord["bells"])], rng) * rng.uniform(0.05, 0.09)
                    stop = min(total, at + len(note))
                    bells[at:stop] += note[: stop - at]
                moment += rng.uniform(1.6, 3.4)
            # A rising and falling arpeggio over the chord: the light, hopeful motion.
            pattern = [0, 1, 2, 3, 4, 3, 2, 1]
            tones = chord["bells"][:5]
            for step in range(int(CHORD_SECONDS / STEP)):
                at = int((start + step * STEP) * RATE)
                if at < 0 or at >= total:
                    continue
                accent = 1.0 if step % 4 == 0 else 0.7
                pan = 0.5 + 0.3 * np.sin(step * 0.7 + index)
                note = pluck(NOTE[tones[pattern[step % len(pattern)]]], pan) * 0.05 * accent
                stop = min(total, at + len(note))
                arp[at:stop] += note[: stop - at]
        start += CHORD_SECONDS
        index += 1

    # Air: soft band of noise that swells and fades.
    t = np.arange(total) / RATE
    band = signal.butter(2, [500, 4200], btype="band", fs=RATE, output="sos")
    air = signal.sosfilt(band, rng.standard_normal((total, 2)), axis=0)
    air *= (0.013 + 0.009 * np.sin(2 * np.pi * 0.045 * t + 1.0))[:, None]

    pads = signal.sosfiltfilt(signal.butter(2, 4800, fs=RATE, output="sos"), pads, axis=0)
    ir = hall(5.0, rng)
    mix = (
        pads * 0.65
        + reverb(pads, ir) * 0.55
        + bass
        + bells * 0.6
        + reverb(bells, ir) * 1.3
        + arp * envelope(total, 10.0, 6.0)[:, None] * 0.55
        + reverb(arp * envelope(total, 10.0, 6.0)[:, None], ir) * 0.7
        + air
        + reverb(air, ir) * 0.5
    )
    # A slow breath over the whole piece.
    mix *= (0.92 + 0.08 * np.sin(2 * np.pi * 0.03 * t))[:, None]

    mix = mix[: int(seconds * RATE)]
    mix *= envelope(len(mix), 2.5, 4.0)[:, None]
    # Calm background level: RMS about -21 dBFS, peaks softly limited below -3 dBFS.
    rms = np.sqrt(np.mean(mix**2))
    mix *= 10 ** (-21 / 20) / max(rms, 1e-9)
    ceiling = 10 ** (-3 / 20)
    mix = ceiling * np.tanh(mix / ceiling)
    return mix


def write_wav(path: str, audio: np.ndarray) -> None:
    data = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(data.tobytes())


def main() -> None:
    seconds = float(sys.argv[1])
    audio = render(seconds)
    write_wav(sys.argv[2], audio)
    peak = 20 * np.log10(np.max(np.abs(audio)) + 1e-12)
    rms = 20 * np.log10(np.sqrt(np.mean(audio**2)) + 1e-12)
    print(f"music: {seconds:.1f} s, peak {peak:.1f} dBFS, rms {rms:.1f} dBFS")


if __name__ == "__main__":
    main()
