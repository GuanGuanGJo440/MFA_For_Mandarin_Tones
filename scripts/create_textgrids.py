#!/usr/bin/env python3
"""
Generate TextGrid files based on /data/wavs_preprocessed and transcripts.xlsx
"""

import os
import wave
import pandas as pd
from textgrid import TextGrid, IntervalTier
from pathlib import Path

print("🗂️ Creating TextGrids...")

# === Path setup ===
base_dir = Path(__file__).resolve().parent.parent
input_folder = base_dir / "data" / "wavs_preprocessed"
output_folder = base_dir / "data" / "textgrids"
excel_path = base_dir / "data" / "Test_SoundRecognition.xlsx"

output_folder.mkdir(exist_ok=True)

# === Load Excel ===
df = pd.read_excel(excel_path, usecols=[0, 1], header=None)
df.columns = ["filename", "word"]
df["filename"] = df["filename"].astype(str).apply(lambda x: os.path.splitext(x)[0].lower())

wav_files = sorted([f for f in input_folder.glob("*.wav")])
wav_basenames = [f.stem.lower() for f in wav_files]

missing_in_excel = [f for f in wav_basenames if f not in df["filename"].tolist()]

if missing_in_excel:
    print("⚠️ Missing entries in Excel for these WAV files:")
    for m in missing_in_excel:
        print(f"  - {m}.wav")
else:
    print("✅ All WAV files are listed in Excel.")

matching_rows = df[df["filename"].isin(wav_basenames)]

if matching_rows.empty:
    print("❌ No matching WAV files found. Check filenames and Excel sheet.")
else:
    print(f"✅ Found {len(matching_rows)} matching entries — generating TextGrids...")

    for _, row in matching_rows.iterrows():
        base = row["filename"]
        word = str(row["word"])
        wav_path = input_folder / f"{base}.wav"

        if not wav_path.exists():
            print(f"⚠️ Skipping missing file: {wav_path.name}")
            continue

        with wave.open(str(wav_path), "r") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            duration = frames / float(rate)

        tg = TextGrid()
        tier = IntervalTier(name="words", minTime=0, maxTime=duration)
        tier.add(0, duration, word)
        tg.append(tier)

        tg.write(str(output_folder / f"{base}.TextGrid"))
        print(f"✅ Created: {base}.TextGrid")

    print(f"🎉 All TextGrids generated successfully in: {output_folder}")
