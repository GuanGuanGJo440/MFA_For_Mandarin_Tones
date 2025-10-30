print("🔧 Modifying TextGrids...")

#!/usr/bin/env python3
"""
Modify TextGrids:
- Input tiers:   Tier 1 = 'words', Tier 2 = 'phones'
- Output tiers:  Tier 1 = 'words' (merged phones, diacritics removed), Tier 2 = 'tones' (numeric 1-4 or 'n')
- Uses midpoint assignment so phones don't get assigned across word boundaries.
- Handles syllabic consonants (e.g. ʐ̩, z̩, n̩) as vowels.
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
MID_TOL = 1e-6  # midpoint tolerance for assignment (seconds)

# IPA sets and diacritic->number mapping
VOWELS = "aAeEiIoOuUyɪʊɤəɛɔɑɨɯɒɚɜ"  
GLIDES = {"j", "w", "ɥ"}
NASALS = {"m", "n", "ŋ"}

DIACR_TO_NUM = {
    "˥":   "1",    # high
    "˧˥": "2",    # rising
    "˨˩˦": "3",   # dipping (3rd)
    "˥˩": "4",    # falling (4th)
    "˧":   "2",
    "˩":   "4",
    "˦":   "2",
    "˨":   "3",
    "˩˧": "3",
}

VOWEL_RE = re.compile(f"[{VOWELS}]")
SYLLABIC_RE = re.compile(r"[̩̍]")  # catches syllabic marks
TONE_DIACR_RE = re.compile(r"[˥˦˧˨˩]+")

# ===================== HELPERS =====================
def is_vowel(phone):
    """Return True if the phone is a vowel or has syllabic diacritic (̩)."""
    if not phone:
        return False
    p = phone.strip()
    # normal vowels
    if VOWEL_RE.search(p):
        return True
    # syllabic diacritic (like ʐ̩, ɻ̩, z̩, s̩)
    if "̩" in p:
        return True
    return False

def is_glide(phone):
    if not phone:
        return False
    s = phone.strip()
    for g in GLIDES:
        if s.startswith(g):
            return True
    return False

def is_nasal(phone):
    return bool(phone and any(n in phone for n in NASALS))

def is_aspirated(phone):
    return bool(phone and ("ʰ" in phone or re.search(r"[ptkbdgcsz]h", phone)))

def extract_tone_diacritic(phone: str) -> str:
    if not phone:
        return ""
    m = TONE_DIACR_RE.search(phone)
    return m.group(0) if m else ""

def diacritic_to_number(diacr: str) -> str:
    if not diacr:
        return "n"
    if diacr in DIACR_TO_NUM:
        return DIACR_TO_NUM[diacr]
    for k in sorted(DIACR_TO_NUM.keys(), key=len, reverse=True):
        if k in diacr:
            return DIACR_TO_NUM[k]
    return "n"

def remove_tone_symbols(phone):
    if phone is None:
        return ""
    return re.sub(r"[˥˦˧˨˩1-5]", "", phone).strip()

def phone_to_tone_number(phone):
    if not phone or phone.strip() == "":
        return ""
    p = phone.strip()
    if p in {"sil", "spn"}:
        return p
    if is_aspirated(p):
        return "ua"
    if is_nasal(p):
        return "un"
    if is_vowel(p):
        diacr = extract_tone_diacritic(p)
        return diacritic_to_number(diacr)
    return "u"

# ===================== CORE: assign phones to word by midpoint =====================
def phones_grouped_by_word(word_tier, phone_tier):
    """
    Return a list aligned to word_tier.intervals: for each word interval an ordered
    list of phone intervals whose midpoint falls inside that word interval.
    """
    # Precompute phone midpoints
    phone_midpoints = [(p, (p.minTime + p.maxTime) / 2.0) for p in phone_tier.intervals]

    grouped = []
    for w in word_tier.intervals:
        wstart, wend = w.minTime, w.maxTime
        phones_here = [p for (p, mid) in phone_midpoints if (mid >= wstart - MID_TOL) and (mid <= wend + MID_TOL)]
        grouped.append(phones_here)
    return grouped


# ===================== MAIN LOGIC =====================
def process_textgrid(in_path, out_path):
    tg = TextGrid.fromFile(in_path)
    word_tier = tg.getFirst(ORIG_WORDS)
    phone_tier = tg.getFirst(ORIG_PHONES)

    # Build grouped phone lists by word using midpoint
    phones_per_word = phones_grouped_by_word(word_tier, phone_tier)

    # --- Create tone tier (numeric) ---
    tone_tier = IntervalTier(name=OUT_TONES, minTime=tg.minTime, maxTime=tg.maxTime)

    # iterate words and their phones
    for w_iv, phones_in_word in zip(word_tier.intervals, phones_per_word):
        # phones_in_word is ordered by original phone_tier order because phone_midpoints preserves order
        i = 0
        N = len(phones_in_word)
        while i < N:
            p = phones_in_word[i]
            ph = (p.mark or "").strip()

            # keep sil or spn as-is
            if ph in {"sil", "spn", ""}:
                tone_tier.addInterval(Interval(p.minTime, p.maxTime, ph))
                i += 1
                continue

            # aspirated consonant -> ua
            if is_aspirated(ph):
                tone_tier.addInterval(Interval(p.minTime, p.maxTime, "ua"))
                i += 1
                continue

            # glide before vowel -> merge with vowel and optional nasal
            if is_glide(ph) and i + 1 < N and is_vowel(phones_in_word[i + 1].mark):
                vowel_iv = phones_in_word[i + 1]
                tone_num = phone_to_tone_number(vowel_iv.mark)
                start = p.minTime
                end = vowel_iv.maxTime
                skip = 2
                if i + 2 < N and is_nasal(phones_in_word[i + 2].mark):
                    end = phones_in_word[i + 2].maxTime
                    skip = 3
                tone_tier.addInterval(Interval(start, end, tone_num))
                i += skip
                continue

            # vowel -> merge with following nasal(s)
            if is_vowel(ph):
                tone_num = phone_to_tone_number(ph)
                start = p.minTime
                end = p.maxTime
                if i + 1 < N and is_nasal(phones_in_word[i + 1].mark):
                    end = phones_in_word[i + 1].maxTime
                    i += 1
                tone_tier.addInterval(Interval(start, end, tone_num))
                i += 1
                continue

            # nasal (stand alone)
            if is_nasal(ph):
                tone_tier.addInterval(Interval(p.minTime, p.maxTime, "un"))
                i += 1
                continue

            # other consonant
            tone_tier.addInterval(Interval(p.minTime, p.maxTime, "u"))
            i += 1

    # compress adjacent identical numeric labels (contiguous) with tolerance
    compressed = []
    MERGE_TOL = 1e-4
    for iv in tone_tier.intervals:
        if not compressed:
            compressed.append(iv)
            continue
        last = compressed[-1]
        if abs(last.maxTime - iv.minTime) < MERGE_TOL and last.mark == iv.mark:
            compressed[-1] = Interval(last.minTime, iv.maxTime, last.mark)
        else:
            compressed.append(iv)
    final_tone_tier = IntervalTier(name=OUT_TONES, minTime=tg.minTime, maxTime=tg.maxTime)
    for iv in compressed:
        final_tone_tier.addInterval(iv)

    # --- Merge phone tier within words (remove IPA diacritics) ---
    merged_phone_tier = IntervalTier(name=OUT_WORDS, minTime=tg.minTime, maxTime=tg.maxTime)
    for w_iv, phones_in_word in zip(word_tier.intervals, phones_per_word):
        # preserve silence/empty word intervals
        if (w_iv.mark or "").strip() in {"", "sil", "spn"}:
            merged_phone_tier.addInterval(Interval(w_iv.minTime, w_iv.maxTime, (w_iv.mark or "").strip()))
            continue

        merged_mark = "".join(remove_tone_symbols(p.mark or "") for p in phones_in_word)
        merged_phone_tier.addInterval(Interval(w_iv.minTime, w_iv.maxTime, merged_mark))

    # --- Save new TextGrid ---
    new_tg = TextGrid()
    new_tg.append(merged_phone_tier)
    new_tg.append(final_tone_tier)
    new_tg.write(out_path)


# ===================== BATCH =====================
def batch_process():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".TextGrid")]
    for f in sorted(files):
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
