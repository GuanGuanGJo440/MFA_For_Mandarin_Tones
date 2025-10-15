#!/usr/bin/env python3
"""
Preprocess WAV files:
- Convert to mono
- Resample to 16kHz
- Save to /data/wavs_preprocessed
"""

import soundfile as sf
import resampy
from pathlib import Path
import numpy as np

print("🎧 Preprocessing WAVs...")

# === Path setup ===
base_dir = Path(__file__).resolve().parent.parent
input_dir = base_dir / "data" / "wavs"
output_dir = base_dir / "data" / "wavs_preprocessed"
output_dir.mkdir(exist_ok=True)

min_samples = 1600  # (~0.1s at 16kHz)
skipped_files = []

for wav_file in input_dir.glob("*.wav"):
    try:
        data, sr = sf.read(wav_file)
    except Exception as e:
        print(f"⚠️ Cannot read {wav_file.name}: {e}")
        skipped_files.append(wav_file.name)
        continue

    # Convert stereo → mono
    if data.ndim > 1:
        data = data.mean(axis=1)

    # Skip too short files
    if len(data) < min_samples:
        skipped_files.append(wav_file.name)
        continue

    # Resample → 16kHz
    if sr != 16000:
        try:
            data = resampy.resample(data, sr, 16000)
            sr = 16000
        except ValueError as e:
            print(f"⚠️ Skipping {wav_file.name}: resampling error {e}")
            skipped_files.append(wav_file.name)
            continue

    # Normalize and convert to 16-bit PCM
    data = data / np.max(np.abs(data)) if np.max(np.abs(data)) > 0 else data
    data_int16 = np.int16(data * 32767)

    sf.write(output_dir / wav_file.name, data_int16, sr, subtype="PCM_16")

print(f"✅ Resampled WAVs saved to: {output_dir}")
if skipped_files:
    print(f"⚠️ Skipped {len(skipped_files)} files: {skipped_files}")
