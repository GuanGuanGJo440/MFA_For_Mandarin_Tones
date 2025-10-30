print("🔧 Modifying TextGrids...")

#!/usr/bin/env python3
"""
Modify TextGrids:
- Input tiers:   Tier 1 = 'words', Tier 2 = 'phones'
- Output tiers:  Tier 1 = 'words' (merged phones, diacritics removed), Tier 2 = 'tones' (numeric 1-4 or 'n')
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

# IPA sets and diacritic->number mapping (adjust if your conventions differ)
VOWELS = "aAeEiIoOuUɪʊɤəɛɔɑɨɯɒɚɜ"
GLIDES = {"j", "w"}
NASALS = {"m", "n", "ŋ"}

DIACR_TO_NUM = {
    "˥":   "1",    # high
    "˧˥": "2",    # rising
    "˨˩˦": "3",   # dipping (3rd)
    "˥˩": "4",    # falling (4th)   <-- adjust if needed
    "˧":   "2",
    "˩":   "4",
    "˦":   "2",
    "˨":   "3",
    "˩˧": "3",
}

VOWEL_RE = re.compile(f"[{VOWELS}]")
TONE_DIACR_RE = re.compile(r"[˥˦˧˨˩]+")

# ===================== HELPERS =====================
def is_vowel(phone):
    return bool(phone and VOWEL_RE.search(phone))

def is_glide(phone):
    return bool(phone and phone.strip() in GLIDES)

def is_nasal(phone):
    return bool(phone and any(n in phone for n in NASALS))

def is_aspirated(phone):
    return bool(phone and ("ʰ" in phone or re.search(r"[ptkbdgcsz]h", phone)))

def extract_tone_diacritic(phone: str) -> str:
    """Return IPA diacritic sequence attached to phone (e.g. '˧˥') or ''."""
    if not phone:
        return ""
    m = TONE_DIACR_RE.search(phone)
    return m.group(0) if m else ""

def diacritic_to_number(diacr: str) -> str:
    """Map diacritic sequence to '1'..'4' or 'n'."""
    if not diacr:
        return "n"
    # exact match first (multi-char keys included)
    if diacr in DIACR_TO_NUM:
        return DIACR_TO_NUM[diacr]
    # fallback: longest key contained in diacritic
    for k in sorted(DIACR_TO_NUM.keys(), key=len, reverse=True):
        if k in diacr:
            return DIACR_TO_NUM[k]
    return "n"

# remove IPA tone diacritics and digits from phone when building merged phone string
def remove_tone_symbols(phone):
    if phone is None:
        return ""
    return re.sub(r"[˥˦˧˨˩1-5]", "", phone).strip()

def phone_to_tone_number(phone):
    """
    Map phone to tone label (numeric):
    - vowel -> numeric tone from diacritic (1-4) or 'n'
    - aspirated consonant -> 'ua'  (we keep these as tokens, but you can change)
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
    return "u"

# ===================== MAIN LOGIC =====================
def process_textgrid(in_path, out_path):
    tg = TextGrid.fromFile(in_path)
    word_tier = tg.getFirst(ORIG_WORDS)
    phone_tier = tg.getFirst(ORIG_PHONES)

    # --- Create tone tier (numeric) ---
    tone_tier = IntervalTier(name=OUT_TONES, minTime=tg.minTime, maxTime=tg.maxTime)

    for word_iv in word_tier.intervals:
        wstart, wend = word_iv.minTime, word_iv.maxTime
        phones_in_word = [p for p in phone_tier.intervals if p.minTime >= wstart - EPS and p.maxTime <= wend + EPS]

        i = 0
        while i < len(phones_in_word):
            p = phones_in_word[i]
            ph = (p.mark or "").strip()

            # keep sil or spn as-is
            if ph in {"sil", "spn", ""}:
                tone_tier.addInterval(Interval(p.minTime, p.maxTime, ph))
                i += 1
                continue

            # glide + vowel merge (use vowel's numeric tone)
            if is_glide(ph) and i + 1 < len(phones_in_word) and is_vowel(phones_in_word[i+1].mark):
                vowel_iv = phones_in_word[i+1]
                tone_num = phone_to_tone_number(vowel_iv.mark)  # vowel -> numeric
                start = p.minTime
                end = vowel_iv.maxTime
                # merge following nasal (if present) into same tone interval
                if i + 2 < len(phones_in_word) and is_nasal(phones_in_word[i+2].mark):
                    end = phones_in_word[i+2].maxTime
                    i += 1
                tone_tier.addInterval(Interval(start, end, tone_num))
                i += 2
                continue

            # vowel + nasal merge (use vowel's numeric tone)
            if is_vowel(ph):
                tone_num = phone_to_tone_number(ph)
                start = p.minTime
                end = p.maxTime
                if i + 1 < len(phones_in_word) and is_nasal(phones_in_word[i+1].mark):
                    end = phones_in_word[i+1].maxTime
                    i += 1
                tone_tier.addInterval(Interval(start, end, tone_num))
                i += 1
                continue

            # consonant -> ua/un/u tokens (kept as labels in tone tier)
            tone_label = phone_to_tone_number(ph)
            tone_tier.addInterval(Interval(p.minTime, p.maxTime, tone_label))
            i += 1

    # Optionally compress adjacent identical numeric labels (contiguous)
    compressed = []
    for iv in tone_tier.intervals:
        if not compressed:
            compressed.append(iv)
            continue
        last = compressed[-1]
        if abs(last.maxTime - iv.minTime) < 1e-8 and last.mark == iv.mark:
            # merge
            compressed[-1] = Interval(last.minTime, iv.maxTime, last.mark)
        else:
            compressed.append(iv)
    final_tone_tier = IntervalTier(name=OUT_TONES, minTime=tg.minTime, maxTime=tg.maxTime)
    for iv in compressed:
        final_tone_tier.addInterval(iv)

    # --- Merge phone tier within words (remove IPA diacritics) ---
    merged_phone_tier = IntervalTier(name=OUT_WORDS, minTime=tg.minTime, maxTime=tg.maxTime)
    for word_iv in word_tier.intervals:
        phones_in_word = [p for p in phone_tier.intervals if p.minTime >= word_iv.minTime - EPS and p.maxTime <= word_iv.maxTime + EPS]

        # preserve silence/empty word intervals
        if (word_iv.mark or "").strip() in {"", "sil", "spn"}:
            merged_phone_tier.addInterval(Interval(word_iv.minTime, word_iv.maxTime, (word_iv.mark or "").strip()))
            continue

        merged_mark = "".join(remove_tone_symbols(p.mark or "") for p in phones_in_word)
        merged_phone_tier.addInterval(Interval(word_iv.minTime, word_iv.maxTime, merged_mark))

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
