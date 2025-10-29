print("🔧 Modifying TextGrids...")

#!/usr/bin/env python3
"""
Modify TextGrids:
- Input tiers:   Tier 1 = 'words', Tier 2 = 'phones'
- Output tiers:  Tier 1 = 'words' (merged phones), Tier 2 = 'tones'
- Input folder:  /Users/guanguangjo/Desktop/original_textgrids
- Output folder: /Users/guanguangjo/Desktop/modified_textgrids
"""

import os
import re
from textgrid import TextGrid, IntervalTier, Interval

# ===================== CONFIG =====================
INPUT_FOLDER = "/Users/guanguangjo/Desktop/original_textgrids"
OUTPUT_FOLDER = "/Users/guanguangjo/Desktop/modified_textgrids"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ORIG_WORDS = "words"
ORIG_PHONES = "phones"

OUT_WORDS = "words"
OUT_TONES = "tones"

EPS = 1e-7

# IPA sets
VOWELS = "aAeEiIoOuUɪʊɤəɛɔɑɨɯɒɚɜ"
GLIDES = {"j", "w"}
NASALS = {"m", "n", "ŋ"}

VOWEL_RE = re.compile(f"[{VOWELS}]")

# ===================== HELPERS =====================
def is_vowel(phone):
    return bool(VOWEL_RE.search(phone))

def is_glide(phone):
    return phone in GLIDES

def is_nasal(phone):
    return phone in NASALS

def is_aspirated(phone):
    return "ʰ" in phone or re.search(r"[ptkbdgcsz]h", phone)

def extract_tone_number(phone):
    """Extract tone number 1–4 from diacritics or digits."""
    if re.search(r"1", phone): return "1"
    if re.search(r"2", phone): return "2"
    if re.search(r"3", phone): return "3"
    if re.search(r"4", phone): return "4"
    return "n"

def remove_tone_symbols(phone):
    """Remove tone digits and diacritics."""
    return re.sub(r"[˥˦˧˨˩1-5]", "", phone).strip()

def phone_to_tone(phone):
    """Map phone to tone label per rules."""
    if not phone or phone.strip() == "":
        return ""
    p = phone.strip()

    # preserve silence or spn
    if p in {"sil", "spn"}:
        return p

    if is_aspirated(p):
        return "ua"
    if is_nasal(p):
        return "un"
    if is_vowel(p):
        return extract_tone_number(p)
    return "u"

# ===================== MAIN LOGIC =====================
def process_textgrid(in_path, out_path):
    tg = TextGrid.fromFile(in_path)
    word_tier = tg.getFirst(ORIG_WORDS)
    phone_tier = tg.getFirst(ORIG_PHONES)

    # --- Create tone tier ---
    tone_tier = IntervalTier(name=OUT_TONES, minTime=tg.minTime, maxTime=tg.maxTime)

    for word_iv in word_tier.intervals:
        word_start, word_end = word_iv.minTime, word_iv.maxTime
        phones_in_word = [
            p for p in phone_tier.intervals
            if p.minTime >= word_start - EPS and p.maxTime <= word_end + EPS
        ]

        i = 0
        while i < len(phones_in_word):
            p = phones_in_word[i]
            ph = p.mark.strip()

            # keep sil or spn as-is
            if ph in {"sil", "spn", ""}:
                tone_tier.addInterval(Interval(p.minTime, p.maxTime, ph))
                i += 1
                continue

            # glide + vowel merge
            if is_glide(ph) and i + 1 < len(phones_in_word) and is_vowel(phones_in_word[i+1].mark):
                v = phones_in_word[i+1]
                tone_label = phone_to_tone(v.mark)
                start, end = p.minTime, v.maxTime
                # merge nasal after vowel
                if i + 2 < len(phones_in_word) and is_nasal(phones_in_word[i+2].mark):
                    end = phones_in_word[i+2].maxTime
                    i += 1
                tone_tier.addInterval(Interval(start, end, tone_label))
                i += 2
                continue

            # vowel + nasal merge
            if is_vowel(ph):
                tone_label = phone_to_tone(ph)
                start, end = p.minTime, p.maxTime
                if i + 1 < len(phones_in_word) and is_nasal(phones_in_word[i+1].mark):
                    end = phones_in_word[i+1].maxTime
                    i += 1
                tone_tier.addInterval(Interval(start, end, tone_label))
                i += 1
                continue

            # consonants
            tone_label = phone_to_tone(ph)
            tone_tier.addInterval(Interval(p.minTime, p.maxTime, tone_label))
            i += 1

    # --- Merge phone tier within words ---
    merged_phone_tier = IntervalTier(name=OUT_WORDS, minTime=tg.minTime, maxTime=tg.maxTime)
    for word_iv in word_tier.intervals:
        phones_in_word = [
            p for p in phone_tier.intervals
            if p.minTime >= word_iv.minTime - EPS and p.maxTime <= word_iv.maxTime + EPS
        ]

        # keep silence or empty
        if word_iv.mark in {"sil", "spn", ""}:
            merged_phone_tier.addInterval(Interval(word_iv.minTime, word_iv.maxTime, word_iv.mark))
            continue

        # merge phones (remove tone symbols)
        merged_mark = "".join(remove_tone_symbols(p.mark) for p in phones_in_word)
        merged_phone_tier.addInterval(Interval(word_iv.minTime, word_iv.maxTime, merged_mark))

    # --- Save new TextGrid ---
    new_tg = TextGrid()
    new_tg.append(merged_phone_tier)
    new_tg.append(tone_tier)
    new_tg.write(out_path)


# ===================== BATCH =====================
def batch_process():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".TextGrid")]
    for f in files:
        inp = os.path.join(INPUT_FOLDER, f)
        outp = os.path.join(OUTPUT_FOLDER, f)
        try:
            process_textgrid(inp, outp)
            print(f"✅ Processed: {f}")
        except Exception as e:
            print(f"❌ Failed: {f} — {e}")

if __name__ == "__main__":
    batch_process()
    print("🎉 Done! All TextGrids saved to:", OUTPUT_FOLDER)
