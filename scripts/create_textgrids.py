print('Creating TextGrids...')

import os
import wave
import pandas as pd
from textgrid import TextGrid, IntervalTier

# ====== CONFIG ======
input_folder = "/Users/guanguangjo/Desktop/files_(online-audio-converter.com)_(6)_5/wavfiles_mono_5"  # folder with wav files
output_folder = "/Users/guanguangjo/Desktop/files_(online-audio-converter.com)_(6)_5/TextGrid_Original_5"  # folder to save TextGrid files
excel_path = "/Users/guanguangjo/Desktop/Test_SoundRecognition.xlsx"  # path to Excel file
sheet_name = "Folder_5"  # sheet name in Excel
# ====================

# Create output folder if not exist
os.makedirs(output_folder, exist_ok=True)

# Load the Excel sheet (column A = filename, column B = word)
df = pd.read_excel(excel_path, sheet_name=sheet_name, usecols=[0, 1], header=None)
df.columns = ["filename", "word"]

# Normalize filenames (remove extensions and lowercase)
df["filename"] = df["filename"].astype(str).apply(lambda x: os.path.splitext(os.path.basename(x))[0].lower())

# List wav files in folder
wav_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".wav")])
wav_basenames = [os.path.splitext(f)[0].lower() for f in wav_files]

# Find missing files
excel_filenames = df["filename"].tolist()
missing_in_excel = [f for f in wav_basenames if f not in excel_filenames]

if missing_in_excel:
    print("⚠️ These WAV files are missing from Excel:")
    for m in missing_in_excel:
        print("  -", m + ".wav")
else:
    print("✅ All WAV files are listed in Excel!")

# Proceed only with matching files
matching_rows = df[df["filename"].isin(wav_basenames)]

if matching_rows.empty:
    print("❌ No matching WAV files found — check filenames and Excel sheet!")
else:
    print(f"✅ Found {len(matching_rows)} matching entries — generating TextGrids...")

    for _, row in matching_rows.iterrows():
        base = row["filename"]
        word = str(row["word"])
        wav_file = base + ".wav"
        wav_path = os.path.join(input_folder, wav_file)

        if not os.path.exists(wav_path):
            print(f"⚠️ Skipping missing file: {wav_file}")
            continue

        # Get duration
        with wave.open(wav_path, 'r') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            duration = frames / float(rate)

        # Create TextGrid
        tg = TextGrid()
        tier = IntervalTier(name="words", minTime=0, maxTime=duration)
        tier.add(0, duration, word)
        tg.append(tier)

        # Save
        textgrid_path = os.path.join(output_folder, base + ".TextGrid")
        tg.write(textgrid_path)

        print(f"✅ Created: {textgrid_path}")

    print(f"🎉 All TextGrids generated successfully in: {output_folder}")
