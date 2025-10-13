print('Generating lexicon dictionary...')

import os
from praatio import tgio
from collections import defaultdict

# --- CONFIG ---
TEXTGRID_DIR = "/Users/guanguangjo/Desktop/TextGrid_Training_10_18_26"
OUTPUT_DICT = "dict.txt"
TONE_TIER = "tones"
WORD_TIER = "words"
TOLERANCE = 0.02  # 20 ms tolerance for time overlap
# --- END CONFIG ---

def extract_word_tone_pairs(tg_path):
    """Extract (word, tone_sequence) pairs from TextGrid."""
    try:
        tg = tgio.openTextgrid(tg_path, ignoreEmptyIntervals=True)
    except TypeError:
        tg = tgio.openTextgrid(tg_path)

    if WORD_TIER not in tg.tierNameList or TONE_TIER not in tg.tierNameList:
        print(f"⚠️ Missing expected tiers in {tg_path}")
        return []

    word_tier = tg.tierDict[WORD_TIER]
    tone_tier = tg.tierDict[TONE_TIER]
    pairs = []

    for start, end, word_label in word_tier.entryList:
        if not word_label.strip():
            continue

        # Find tones overlapping this word (with tolerance)
        tone_segments = [
            (s, e, l)
            for (s, e, l) in tone_tier.entryList
            if (s >= start - TOLERANCE and e <= end + TOLERANCE and l.strip())
        ]

        if not tone_segments:
            continue

        # Combine tone labels in order
        tone_sequence = " ".join([l for _, _, l in tone_segments])
        pairs.append((word_label.strip(), tone_sequence))

    return pairs


def main():
    word_dict = defaultdict(set)
    files = [f for f in os.listdir(TEXTGRID_DIR) if f.endswith(".TextGrid")]
    print(f"📂 Found {len(files)} TextGrid files")

    for filename in files:
        tg_path = os.path.join(TEXTGRID_DIR, filename)
        pairs = extract_word_tone_pairs(tg_path)
        for word, tone_seq in pairs:
            word_dict[word].add(tone_seq)

    # Write dictionary file
    with open(OUTPUT_DICT, "w", encoding="utf-8") as f:
        for word, variants in sorted(word_dict.items()):
            for pron in variants:
                f.write(f"{word}\t{pron}\n")

    print(f"✅ Dictionary written to {OUTPUT_DICT} with {len(word_dict)} entries.")


if __name__ == "__main__":
    main()
