#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate lexicon dictionary from modified TextGrids.

Input:  /data/textgrids_modified/
Output: /data/dict/dict.txt  and  /data/dict/dict.dict

Run:
    python scripts/generate_dictionary.py
"""

import os
from pathlib import Path
from praatio import tgio
from collections import defaultdict

print("🔧 Generating lexicon dictionary...")

# ========== CONFIG ==========
BASE_DIR = Path(__file__).resolve().parent.parent
TEXTGRID_DIR = BASE_DIR / "data" / "textgrids_modified"
OUTPUT_DIR = BASE_DIR / "data" / "dict"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_TXT = OUTPUT_DIR / "dict.txt"
OUTPUT_DICT = OUTPUT_DIR / "dict.dict"

TONE_TIER = "tones"
WORD_TIER = "words"
TOLERANCE = 0.02  # 20 ms
# =============================


def extract_word_tone_pairs(tg_path):
    """Extract (word, tone_sequence) pairs from TextGrid."""
    try:
        tg = tgio.openTextgrid(tg_path, ignoreEmptyIntervals=True)
    except TypeError:
        tg = tgio.openTextgrid(tg_path)

    if WORD_TIER not in tg.tierNameList or TONE_TIER not in tg.tierNameList:
        print(f"⚠️ Missing expected tiers in {tg_path.name}")
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
    tg_files = sorted(TEXTGRID_DIR.glob("*.TextGrid"))

    print(f"📂 Found {len(tg_files)} TextGrid files in {TEXTGRID_DIR}")

    for tg_path in tg_files:
        pairs = extract_word_tone_pairs(tg_path)
        for word, tone_seq in pairs:
            word_dict[word].add(tone_seq)

    # --- Write dictionary to TXT and DICT ---
    for out_path in [OUTPUT_TXT, OUTPUT_DICT]:
        with open(out_path, "w", encoding="utf-8") as f:
            for word, variants in sorted(word_dict.items()):
                for pron in sorted(variants):
                    f.write(f"{word}\t{pron}\n")
        print(f"✅ Dictionary written to {out_path}")

    print(f"🎉 Done! {len(word_dict)} unique entries written.")


if __name__ == "__main__":
    main()
