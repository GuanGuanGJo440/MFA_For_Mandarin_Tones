#!/usr/bin/env python3
import os
import csv
from textgrid import TextGrid

# === Paths ===
base_dir = Path(__file__).resolve().parent.parent
input_folder = base_dir / "data_train" / "training_corpus"
output_folder = base_dir / "data_train" / "corpus_stats"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "tone_counts_total.csv")

# === Initialize total counters ===
tone_counts = {"1": 0, "2": 0, "3": 0, "4": 0, "n": 0}

# === Process TextGrids ===
for filename in os.listdir(input_dir):
    if not filename.endswith(".TextGrid"):
        continue

    tg_path = os.path.join(input_dir, filename)
    try:
        tg = TextGrid.fromFile(tg_path)
        # Tier 2 (index 1) assumed to contain tones
        tone_tier = tg[1]
    except Exception as e:
        print(f"⚠️ Error reading {filename}: {e}")
        continue

    for interval in tone_tier:
        label = interval.mark.strip()
        if label in tone_counts:
            tone_counts[label] += 1

# === Write total counts to CSV ===
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["tone", "count"])
    for tone, count in tone_counts.items():
        writer.writerow([tone, count])

print("✅ Done!")
print(f"Total tone counts saved to: {output_path}")
for tone, count in tone_counts.items():
    print(f"Tone {tone}: {count}")
