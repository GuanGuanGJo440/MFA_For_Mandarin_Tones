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
from pathlib import Path

print("🔧 Modifying TextGrids to Phones and Tones...")

# ===================== CONFIG =====================
base_dir = Path(__file__).resolve().parent.parent
INPUT_FOLDER = base_dir / "data_train" / "textgrids"
OUTPUT_FOLDER = base_dir / "data_train" / "textgrids_modified"
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
RHOTIC = "ɻ"  # rhotic symbol to be treated like a following-nasal when after vowel/glide

DIACR_TO_NUM = {
    "˥":   "1",    # high
    "˧˥": "2",    # rising
    "˨˩˦": "3",   # dipping (3rd)
    "˥˩": "4",    # falling (4th)
    "˧":   "n",
    "˩":   "n",
    "˦":   "1",
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
    if VOWEL_RE.search(p):
        return True
    if "̩" in p or "̍" in p:
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

def is_rhotic(phone):
    """True if phone is ɻ or contains ɻ (possibly with diacritics)."""
    if not phone:
        return False
    return "ɻ" in phone

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
    """
    Map phone to tone label (numeric):
    - vowel -> numeric tone from diacritic (1-4) or 'n'
    - aspirated consonant -> 'ua'
    - nasal consonant -> 'un'
    - other consonant -> 'u'
    - preserve 'sil' and 'spn'
    """
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
    # treat an isolated rhotic (not after vowel) as consonant
    if is_rhotic(p):
        return "u"
    return "u"

# ===================== CORE: assign phones to word by midpoint =====================
def phones_grouped_by_word(word_tier, phone_tier):
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

    phones_per_word = phones_grouped_by_word(word_tier, phone_tier)

    # --- Create tone intervals per word ---
    tone_tier = IntervalTier(name=OUT_TONES, minTime=tg.minTime, maxTime=tg.maxTime)
    tone_items = []  # store (Interval, word_index)

    for widx, (w_iv, phones_in_word) in enumerate(zip(word_tier.intervals, phones_per_word)):
        i = 0
        N = len(phones_in_word)
        while i < N:
            p = phones_in_word[i]
            ph = (p.mark or "").strip()

            # keep sil or spn as-is
            if ph in {"sil", "spn", ""}:
                iv = Interval(p.minTime, p.maxTime, ph)
                tone_tier.addInterval(iv)
                tone_items.append((iv, widx))
                i += 1
                continue

            # aspirated consonant -> ua
            if is_aspirated(ph):
                iv = Interval(p.minTime, p.maxTime, "ua")
                tone_tier.addInterval(iv)
                tone_items.append((iv, widx))
                i += 1
                continue

            # glide before vowel -> merge with vowel and optional nasal or rhotic
            if is_glide(ph) and i + 1 < N and is_vowel(phones_in_word[i + 1].mark):
                vowel_iv = phones_in_word[i + 1]
                tone_num = phone_to_tone_number(vowel_iv.mark)
                start = p.minTime
                end = vowel_iv.maxTime
                skip = 2
                # merge nasal or rhotic after vowel
                if i + 2 < N and (is_nasal(phones_in_word[i + 2].mark) or is_rhotic(phones_in_word[i + 2].mark)):
                    end = phones_in_word[i + 2].maxTime
                    skip = 3
                iv = Interval(start, end, tone_num)
                tone_tier.addInterval(iv)
                tone_items.append((iv, widx))
                i += skip
                continue

            # vowel -> merge with following nasal(s) or rhotic if present
            if is_vowel(ph):
                tone_num = phone_to_tone_number(ph)
                start = p.minTime
                end = p.maxTime
                if i + 1 < N and (is_nasal(phones_in_word[i + 1].mark) or is_rhotic(phones_in_word[i + 1].mark)):
                    end = phones_in_word[i + 1].maxTime
                    i += 1
                iv = Interval(start, end, tone_num)
                tone_tier.addInterval(iv)
                tone_items.append((iv, widx))
                i += 1
                continue

            # nasal (standalone)
            if is_nasal(ph):
                iv = Interval(p.minTime, p.maxTime, "un")
                tone_tier.addInterval(iv)
                tone_items.append((iv, widx))
                i += 1
                continue

            # rhotic standalone (not following vowel) -> treat as consonant 'u'
            if is_rhotic(ph):
                iv = Interval(p.minTime, p.maxTime, "u")
                tone_tier.addInterval(iv)
                tone_items.append((iv, widx))
                i += 1
                continue

            # other consonant
            iv = Interval(p.minTime, p.maxTime, "u")
            tone_tier.addInterval(iv)
            tone_items.append((iv, widx))
            i += 1

    # --- Compress adjacent identical labels (within same word) ---
    MERGE_TOL = 1e-4
    compressed_items = []
    for iv, widx in tone_items:
        if not compressed_items:
            compressed_items.append((iv, widx))
            continue
        last_iv, last_widx = compressed_items[-1]
        if last_widx == widx and last_iv.mark == iv.mark and abs(last_iv.maxTime - iv.minTime) < MERGE_TOL:
            merged = Interval(last_iv.minTime, iv.maxTime, last_iv.mark)
            compressed_items[-1] = (merged, last_widx)
        else:
            compressed_items.append((iv, widx))

    # --- Build final tone tier ---
    final_tone_tier = IntervalTier(name=OUT_TONES, minTime=tg.minTime, maxTime=tg.maxTime)
    for iv, _ in compressed_items:
        final_tone_tier.addInterval(iv)

    # --- Merge phones for words tier ---
    merged_word_tier = IntervalTier(name=OUT_WORDS, minTime=tg.minTime, maxTime=tg.maxTime)
    for w_iv, phones_in_word in zip(word_tier.intervals, phones_per_word):
        label = (w_iv.mark or "").strip()
        if label in {"", "sil", "spn"}:
            merged_word_tier.addInterval(Interval(w_iv.minTime, w_iv.maxTime, label))
            continue
        merged_label = "".join(remove_tone_symbols(p.mark or "") for p in phones_in_word)
        merged_word_tier.addInterval(Interval(w_iv.minTime, w_iv.maxTime, merged_label))

    # --- Write new TextGrid ---
    new_tg = TextGrid()
    new_tg.append(merged_word_tier)
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
