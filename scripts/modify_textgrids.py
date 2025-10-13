print('Modifying TextGrids...')

# Jupyter-ready cell — drop into a notebook and run
import os, re
from textgrid import TextGrid, Interval, IntervalTier

# -------------- CONFIG --------------
input_dir = "/Users/guanguangjo/Desktop/edit_TextGrid_input_Training_26"
output_dir = "/Users/guanguangjo/Desktop/edit_TextGrid_output_Training_26"
os.makedirs(output_dir, exist_ok=True)

# phoneme classes (edit/extend if your inventory has extras)
ASPIRATED = {"pʰ", "tʰ", "kʰ", "tsʰ", "tɕʰ", "ʈʂʰ"}
NASALS = {"m", "n", "ŋ"}
GLIDES = {"j", "w", "ɥ"}     # medial glides to be merged into vowel tone
# basic vowel bases/diphthongs and syllabic nasals from your dictionary
VOWEL_BASES = {"a","e","i","o","u","y","ə","ɤ","ɚ","ɨ","ʊ","ɯ","œ",
               "aw","ow","aj","ej","n̩","ŋ̍","z̩","ʐ̩","aj","aw","ow"}

# -------------- HELPERS --------------
def get_tone_number(label: str) -> str:
    """Map Chao-style tone marks to 1/2/3/4 or 'n' (neutral)."""
    if "˥˩" in label:      # falling contour
        return "4"
    if "˨˩˦" in label:     # dipping
        return "3"
    if "˧˥" in label:      # rising
        return "2"
    if "˥" in label:       # high
        return "1"
    # treat bare ˩ or no explicit mark as neutral
    return "n"

def is_empty_label(label: str) -> bool:
    return label.strip() == ""

def is_aspirated(label: str) -> bool:
    return any(label.startswith(x) for x in ASPIRATED)

def is_nasal(label: str) -> bool:
    # check for 'n', 'm', 'ŋ' possibly with diacritics (e.g., n̩, n̩˥˩)
    l = label.strip()
    return any(l.startswith(x) for x in NASALS) or l.startswith("n̩") or l.startswith("ŋ̍")

def is_glide(label: str) -> bool:
    l = label.strip()
    return any(l.startswith(x) for x in GLIDES)

def is_vowel_like(label: str) -> bool:
    if is_empty_label(label):
        return False
    l = label.strip()
    # direct substring check for multi-char vowel forms/diphthongs
    for v in VOWEL_BASES:
        if l.startswith(v) or (len(v) > 1 and v in l):
            return True
    # fallback: any vowel character present
    return bool(re.search(r"[aeiouəɤɯɪʊy]", l))

def classify_onset(label: str) -> str:
    """Map a consonant onset label to ua/un/u."""
    if is_aspirated(label):
        return "ua"
    if is_nasal(label):
        return "un"
    # default consonant
    return "u"

# -------------- PROCESSING --------------
def process_file(in_path, out_path):
    tg = TextGrid.fromFile(in_path)

    # find tiers by name ("words" and "phones"). We support multiple TextGrid shapes:
    # attempt getFirst (if available) else fall back to index-based search
    def find_tier_by_name(tg_obj, name):
        # try common API
        try:
            tier = tg_obj.getFirst(name)
            return tier
        except Exception:
            pass
        # iterate through tiers
        try:
            for t in tg_obj:
                if getattr(t, "name", "").lower() == name.lower():
                    return t
        except Exception:
            pass
        # index fallback
        try:
            for i in range(len(tg_obj)):
                t = tg_obj[i]
                if getattr(t, "name", "").lower() == name.lower():
                    return t
        except Exception:
            pass
        raise ValueError(f"Tier named '{name}' not found in {in_path}")

    words_tier = find_tier_by_name(tg, "words")
    phones_tier = find_tier_by_name(tg, "phones")

    phone_intervals = phones_tier.intervals    # list of Interval objects
    word_intervals = words_tier.intervals

    # Partition phones by word (enforce hard boundaries)
    # We'll walk phone intervals with a pointer and for each word collect the phone indices falling within it.
    phone_idx = 0
    new_tone_entries = []

    for w in word_intervals:
        w_start, w_end = w.minTime, w.maxTime

        # collect indices of phones inside this word (by phone start time)
        indices = []
        while phone_idx < len(phone_intervals) and phone_intervals[phone_idx].minTime < w_end:
            if phone_intervals[phone_idx].minTime >= w_start and phone_intervals[phone_idx].minTime < w_end:
                indices.append(phone_idx)
            phone_idx += 1

        # If no phones inside this word, continue (word may be silence)
        if not indices:
            continue

        i = 0
        while i < len(indices):
            idx = indices[i]
            itv = phone_intervals[idx]
            lab = itv.mark.strip()
            s = itv.minTime
            e = itv.maxTime

            # 1) empty -> preserve as empty interval (do not merge across)
            if is_empty_label(lab):
                new_tone_entries.append((s, e, ""))
                i += 1
                continue

            # 2) aspirated onset -> own 'ua'
            if is_aspirated(lab):
                new_tone_entries.append((s, e, "ua"))
                i += 1
                continue

            # 3) nasal that functions as onset (i.e., followed by a vowel inside same word) -> 'un'
            # detect next phone in same word
            next_i = i + 1
            if is_nasal(lab):
                if next_i < len(indices):
                    nxt = phone_intervals[indices[next_i]].mark.strip()
                    if not is_empty_label(nxt) and is_vowel_like(nxt):
                        # nasal-onset -> keep separate 'un'
                        new_tone_entries.append((s, e, "un"))
                        i += 1
                        continue
                # else: treat as isolated nasal (no vowel following) -> 'un'
                new_tone_entries.append((s, e, "un"))
                i += 1
                continue

            # 4) regular consonant onset (non-glide, non-nasal) -> 'u'
            if not (is_glide(lab) or is_vowel_like(lab)):
                # it's a plain consonant onset (not glide) -> u
                new_tone_entries.append((s, e, "u"))
                i += 1
                continue

            # 5) Otherwise this is glide or vowel-like -> start building a merged syllable (medial+vowel+coda_nasal)
            # begin merged syllable at current interval start
            merged_start = s
            merged_end = e
            tone_label = None
            found_vowel = False

            k = i
            while k < len(indices):
                idxk = indices[k]
                labk = phone_intervals[idxk].mark.strip()

                # stop if empty interval encountered (do not cross empty)
                if is_empty_label(labk):
                    break

                if is_glide(labk):
                    # include glide into the merged syllable (glide before vowel)
                    merged_end = phone_intervals[idxk].maxTime
                    k += 1
                    continue

                if is_vowel_like(labk):
                    # include vowel-like
                    merged_end = phone_intervals[idxk].maxTime
                    found_vowel = True
                    t = get_tone_number(labk)
                    # prefer explicit tone > neutral
                    if t != "n":
                        tone_label = t
                    elif tone_label is None:
                        tone_label = "n"
                    k += 1
                    continue

                # if we find nasal immediately after vowel, include as coda and continue
                if is_nasal(labk) and found_vowel:
                    merged_end = phone_intervals[idxk].maxTime
                    k += 1
                    # continue trying to include multiple immediate nasals if any
                    continue

                # otherwise we've reached a next-syllable onset — stop
                break

            # If we did not find any vowel in this chunk, treat the current token as onset consonant
            if not found_vowel:
                # fallback classification for current interval
                mapped = classify_onset(lab)
                new_tone_entries.append((s, e, mapped))
                i += 1
                continue

            # ensure a tone label (default neutral)
            if tone_label is None:
                tone_label = "n"

            # append merged syllable with tone_label
            new_tone_entries.append((merged_start, merged_end, tone_label))
            # consume indices up to k-1
            consumed = k - i
            i += consumed

    # After walking words, there might be phones that start after the last word (e.g., trailing phones) — process leftover phones
    # (phone_idx currently points to the next phone after last processed by words loop)
    # If there are phones earlier than first word (phone_idx progressed), we also need to handle phones before the first word.
    # To be robust, process ANY phone index not yet covered by new_tone_entries:
    # Build a set of times already covered, then fill uncovered phones by simple mapping
    covered = []
    for s,e,l in new_tone_entries:
        covered.append((s,e))

    # Helper: check if a phone interval start is already covered by some (s,e)
    def is_covered(start_time):
        for a,b in covered:
            if a <= start_time < b:
                return True
        return False

    # process all phones and add ones not covered (these might be before/after words)
    for p in phone_intervals:
        if is_covered(p.minTime):
            continue
        lab = p.mark.strip()
        if is_empty_label(lab):
            new_tone_entries.append((p.minTime, p.maxTime, ""))
            continue
        # if token is vowel-like, label by tone and include trailing nasals if any (simple local rule)
        if is_vowel_like(lab):
            tone = get_tone_number(lab)
            new_tone_entries.append((p.minTime, p.maxTime, tone))
            continue
        # consonant fallback
        new_tone_entries.append((p.minTime, p.maxTime, classify_onset(lab)))

    # sort entries by start time (just in case)
    new_tone_entries.sort(key=lambda x: x[0])

    # Build Interval objects and the new tier
    tone_tier = IntervalTier("tones", phones_tier.minTime, phones_tier.maxTime)
    tone_intervals = [ Interval(s,e,l) for (s,e,l) in new_tone_entries ]
    tone_tier.intervals.extend(tone_intervals)

    # append the new tier to textgrid (does not remove phones)
    tg.append(tone_tier)

    # Delete the Phones Tier
    tg.tiers.remove(tg[1])
    
    # save
    tg.write(out_path)
    print(f"Saved: {out_path}")

# Run on all files in input_dir
for fname in os.listdir(input_dir):
    if not fname.endswith(".TextGrid"):
        continue
    in_path = os.path.join(input_dir, fname)
    out_path = os.path.join(output_dir, fname)
    process_file(in_path, out_path)

print("All done.")
