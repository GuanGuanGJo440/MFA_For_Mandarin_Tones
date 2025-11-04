#!/usr/bin/env python3
"""
Generate TextGrid files based on /data_train/wavs_preprocessed and transcripts.xlsx
Preserves the original filename capitalization.
"""

import os
import wave
import pandas as pd
from textgrid import TextGrid, IntervalTier
from pathlib import Path

print("🗂️ Creating TextGrids...")

# ===================== CONFIG =====================
# === Path setup ===
base_dir = Path(__file__).resolve().parent.parent
input_folder = base_dir / "data_train" / "wavs_preprocessed"
output_folder = base_dir / "data_train" / "textgrids"
excel_path = base_dir / "data_train" / "speech_sample_texts.xlsx"

output_folder.mkdir(exist_ok=True)

# === Load Excel ===
df = pd.read_excel(excel_path, usecols=[0, 1], header=None)
df.columns = ["filename", "word"]

# Normalize Excel filenames for matching (lowercase, no extension)
df["filename_norm"] = df["filename"].astype(str).apply(
    lambda x: os.path.splitext(os.path.basename(x))[0].lower()
)

# List all wav files (keep original names)
wav_files = sorted(input_folder.glob("*.wav"))

# Build a map from lowercase → original-case stem
wav_case_map = {f.stem.lower(): f.stem for f in wav_files}

# Check which wav files are missing from Excel
missing_in_excel = [stem for stem in wav_case_map.keys() if stem not in df["filename_norm"].tolist()]

if missing_in_excel:
    print("⚠️ Missing entries in Excel for these WAV files:")
    for m in missing_in_excel:
        print(f"  - {wav_case_map[m]}.wav")
else:
    print("✅ All WAV files are listed in Excel.")

# Filter only matching rows (case-insensitive)
matching_rows = df[df["filename_norm"].isin(wav_case_map.keys())]

if matching_rows.empty:
    print("❌ No matching WAV files found. Check filenames and Excel sheet.")
else:
    print(f"✅ Found {len(matching_rows)} matching entries — generating TextGrids...")

    for _, row in matching_rows.iterrows():
        base_lower = row["filename_norm"]
        word = str(row["word"])
        base_original = wav_case_map[base_lower]  # restore original case
        wav_path = input_folder / f"{base_original}.wav"

        if not wav_path.exists():
            print(f"⚠️ Skipping missing file: {wav_path.name}")
            continue

        # Get duration
        with wave.open(str(wav_path), "r") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            duration = frames / float(rate)

        # Create TextGrid
        tg = TextGrid()
        tier = IntervalTier(name="words", minTime=0, maxTime=duration)
        tier.add(0, duration, word)
        tg.append(tier)

        # Save with original capitalization
        output_path = output_folder / f"{base_original}.TextGrid"
        tg.write(str(output_path))
        print(f"✅ Created: {output_path.name}")

    print(f"🎉 All TextGrids generated successfully in: {output_folder}")

