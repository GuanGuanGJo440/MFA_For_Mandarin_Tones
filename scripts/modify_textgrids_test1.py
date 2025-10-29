#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modify TextGrids for MFA Mandarin tone model training.
This script processes TextGrid files in /data/textgrids_pretrained
and outputs modified versions to /data/textgrids_train.

Run:
    python scripts/modify_textgrids.py
"""

import os
import re
from pathlib import Path
from textgrid import TextGrid, Interval, IntervalTier

print("🔧 Modifying TextGrids...")

# ========== CONFIG ==========
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "data" / "textgrids_pretrained"
OUTPUT_DIR = BASE_DIR / "data" / "textgrids_modified"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# phoneme classes
ASPIRATED = {"pʰ", "tʰ", "kʰ", "tsʰ", "tɕʰ", "ʈʂʰ"}
NASALS = {"m", "n", "ŋ"}
GLIDES = {"j", "w", "ɥ"}
VOWEL_BASES = {
    "a","e","i","o","u","y","ə","ɤ","ɚ","ɨ","ʊ","ɯ","œ",
    "aw","ow","aj","ej","n̩","ŋ̍","z̩","ʐ̩"
}

# ========== HELPERS ==========
def get_tone_number(label: str) -> str:
    """Convert tone marks to 1/2/3/4/n."""
    if "˥˩" in label: return "4"
    if "˨˩˦" in label: return "3"
    if "˧˥" in label: return "2"
    if "˥" in label: return "1"
    return "n"

def is_empty(label: str) -> bool:
    return label.strip() == ""

def is_aspirated(label: str) -> bool:
    return any(label.startswith(x) for x in ASPIRATED)

def is_nasal(label: str) -> bool:
    l = label.strip()
    return any(l.startswith(x) for x in NASALS) or l.startswith("n̩") or l.startswith("ŋ̍")

def is_glide(label: str) -> bool:
    return any(label.strip().startswith(x) for x in GLIDES)

def is_vowel_like(label: str) -> bool:
    if is_empty(label):
        return False
    l = label.strip()
    return any(l.startswith(v) or (len(v) > 1 and v in l) for v in VOWEL_BASES)

def classify_onset(label: str) -> str:
    """Map consonant onsets to generic u/un/ua."""
    if is_aspirated(label): return "ua"
    if is_nasal(label): return "un"
    return "u"

# ========== MAIN FUNCTION ==========
def process_file(in_path: Path, out_path: Path):
    tg = TextGrid.fromFile(in_path)

    # find tiers by name
    def find_tier(tg_obj, name):
        for tier in tg_obj.tiers:
            if tier.name.lower() == name.lower():
                return tier
        raise ValueError(f"Tier '{name}' not found in {in_path.name}")

    words_tier = find_tier(tg, "words")
    phones_tier = find_tier(tg, "phones")

    new_tone_entries = []
    phone_intervals = phones_tier.intervals
    word_intervals = words_tier.intervals

    phone_idx = 0
    for w in word_intervals:
        w_start, w_end = w.minTime, w.maxTime
        indices = []
        while phone_idx < len(phone_intervals) and phone_intervals[phone_idx].minTime < w_end:
            if phone_intervals[phone_idx].minTime >= w_start:
                indices.append(phone_idx)
            phone_idx += 1

        if not indices:
            continue

        i = 0
        while i < len(indices):
            idx = indices[i]
            itv = phone_intervals[idx]
            s, e, lab = itv.minTime, itv.maxTime, itv.mark.strip()

            if is_empty(lab):
                new_tone_entries.append((s, e, ""))
                i += 1
                continue
            if is_aspirated(lab):
                new_tone_entries.append((s, e, "ua"))
                i += 1
                continue
            if is_nasal(lab):
                if i + 1 < len(indices):
                    nxt = phone_intervals[indices[i + 1]].mark.strip()
                    if is_vowel_like(nxt):
                        new_tone_entries.append((s, e, "un"))
                        i += 1
                        continue
                new_tone_entries.append((s, e, "un"))
                i += 1
                continue
            if not (is_glide(lab) or is_vowel_like(lab)):
                new_tone_entries.append((s, e, "u"))
                i += 1
                continue

            merged_start, merged_end, tone_label = s, e, None
            found_vowel = False
            k = i
            while k < len(indices):
                labk = phone_intervals[indices[k]].mark.strip()
                if is_empty(labk): break
                if is_glide(labk) or is_vowel_like(labk) or is_nasal(labk):
                    merged_end = phone_intervals[indices[k]].maxTime
                    if is_vowel_like(labk):
                        found_vowel = True
                        t = get_tone_number(labk)
                        if t != "n": tone_label = t
                        elif tone_label is None: tone_label = "n"
                    k += 1
                else:
                    break
            if not found_vowel:
                new_tone_entries.append((s, e, classify_onset(lab)))
                i += 1
                continue
            if tone_label is None:
                tone_label = "n"
            new_tone_entries.append((merged_start, merged_end, tone_label))
            i = k

    # sort and rebuild
    new_tone_entries.sort(key=lambda x: x[0])
    tone_tier = IntervalTier("tones", phones_tier.minTime, phones_tier.maxTime)
    for s, e, l in new_tone_entries:
        tone_tier.add(s, e, l)

    # append new tier, remove old phones tier
    tg.append(tone_tier)
    tg.tiers.remove(phones_tier)

    tg.write(out_path)
    print(f"✅ Saved: {out_path.name}")

# ========== RUN ALL ==========
for tg_file in sorted(INPUT_DIR.glob("*.TextGrid")):
    out_path = OUTPUT_DIR / tg_file.name
    process_file(tg_file, out_path)

print(f"🎉 Done! Modified TextGrids saved to: {OUTPUT_DIR}")
