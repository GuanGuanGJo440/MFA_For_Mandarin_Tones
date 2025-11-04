import os
from textgrid import TextGrid, Interval, IntervalTier
import re
from pathlib import Path

print("🔧 Modifying TextGrids to Only Phones...")

# ===================== CONFIG =====================
# === Path setup ===
base_dir = Path(__file__).resolve().parent.parent
input_folder = base_dir / "data_test" / "output_textgrids_pretrained_original"
output_folder = base_dir / "data_test" / "output_textgrids_pretrained_modified"

os.makedirs(output_folder, exist_ok=True)

# ====== IPA tone removal ======
# Covers common Mandarin tone diacritics and Chao tone letters
IPA_TONE_PATTERN = r'[˥˦˧˨˩ˀˇˊˋ˙]'

def remove_tone_symbols(label):
    """Remove IPA tone marks (˥ ˦ ˧ ˨ ˩ ˀ ˇ ˊ ˋ ˙) from a phone label."""
    return re.sub(IPA_TONE_PATTERN, '', label)

def merge_phones_by_word(word_tier, phone_tier):
    """Merge phones belonging to the same word interval."""
    merged_intervals = []
    for word_interval in word_tier:
        word_start = word_interval.minTime
        word_end = word_interval.maxTime
        word_label = word_interval.mark.strip()

        # Find phones within this word
        phones_in_word = [
            p for p in phone_tier
            if p.minTime >= word_start and p.maxTime <= word_end and p.mark.strip()
        ]

        # Merge phone labels (remove tone symbols)
        merged_label = "".join(remove_tone_symbols(p.mark) for p in phones_in_word)

        # Handle silence / empty intervals
        if word_label == "" or word_label in ["sil", "spn"]:
            merged_label = word_label

        merged_intervals.append(Interval(word_start, word_end, merged_label))
    return merged_intervals


# ====== MAIN LOOP ======
for filename in os.listdir(input_folder):
    if not filename.endswith(".TextGrid"):
        continue

    tg_path = os.path.join(input_folder, filename)
    tg = TextGrid()
    tg.read(tg_path)

    if len(tg.tiers) < 2:
        print(f"Skipping {filename}: not enough tiers")
        continue

    word_tier = tg.tiers[0]
    phone_tier = tg.tiers[1]

    merged_tier = IntervalTier(name="words", minTime=tg.minTime, maxTime=tg.maxTime)
    merged_intervals = merge_phones_by_word(word_tier, phone_tier)

    for iv in merged_intervals:
        merged_tier.addInterval(iv)

    new_tg = TextGrid(minTime=tg.minTime, maxTime=tg.maxTime)
    new_tg.append(merged_tier)

    out_path = os.path.join(output_folder, filename)
    new_tg.write(out_path)
    print(f"Processed: {filename}")

print("✅ All TextGrids processed successfully (IPA tone symbols removed).")
