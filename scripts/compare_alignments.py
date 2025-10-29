print('Comparing alignments...')

import os
import re
from collections import Counter, defaultdict
from textgrid import TextGrid
import pandas as pd

# ===== CONFIG =====
trained_folder = "/Users/guanguangjo/Desktop/MFA_Align_Output_Trained"
pretrained_folder = "/Users/guanguangjo/Desktop/MFA_Align_Output_Pretrained"
threshold = 0.2  # seconds (200 ms)
word_tier_name = "words"
# Tier2 possible names in trained / pretrained (will pick first that exists)
tier2_candidates = ["phones", "phone", "tones", "tone"]
# ==================

def extract_tier(textgrid, tier_name):
    """Return tier by name (case-insensitive) or None."""
    for tier in textgrid.tiers:
        if tier.name.strip().lower() == tier_name.strip().lower():
            return tier
    return None

def find_tier2(textgrid):
    """Find a tier among candidate names and return it (or None)."""
    for name in tier2_candidates:
        t = extract_tier(textgrid, name)
        if t is not None:
            return t, name
    return None, None

def extract_tone_label(s):
    """Return a tone token from a phone label: '1' '2' '3' '4' 'n' or 'unknown'."""
    if s is None:
        return "unknown"
    s = s.strip()
    # search for digits 1-4 or letter n (commonly used for neutral)
    m = re.search(r"([1234])", s)
    if m:
        return m.group(1)
    if re.search(r"\bn\b", s):  # standalone n
        return "n"
    # sometimes 'N' or '0' might be used for neutral; treat as 'n' if found
    if re.search(r"\b0\b", s) or re.search(r"\bN\b", s):
        return "n"
    return "unknown"

def phones_in_interval(tier, interval_start, interval_end):
    """Return list of phone intervals that overlap (even partially) with given word interval,
       sorted by start time."""
    phones = []
    for p in tier.intervals:
        # overlap check
        if p.maxTime > interval_start and p.minTime < interval_end:
            phones.append(p)
    phones.sort(key=lambda x: x.minTime)
    return phones

def compare_intervals(trained_file, pretrained_file, threshold):
    tg_tr = TextGrid.fromFile(trained_file)
    tg_pr = TextGrid.fromFile(pretrained_file)

    # Tier1 (word) - must be present in both
    tier_tr_word = extract_tier(tg_tr, word_tier_name)
    tier_pr_word = extract_tier(tg_pr, word_tier_name)
    if not (tier_tr_word and tier_pr_word):
        # Try case-insensitive name mismatch
        return {"error": f"missing word tier in {os.path.basename(trained_file)} or pretrained."}

    # Tier2: find in each; they may be named differently
    tier_tr_t2, tr_t2_name = find_tier2(tg_tr)
    tier_pr_t2, pr_t2_name = find_tier2(tg_pr)
    if not (tier_tr_t2 and tier_pr_t2):
        return {"error": f"missing Tier-2 (phones/tones) in {os.path.basename(trained_file)} or pretrained."}

    results = []
    unmatched_stats = {"trained_extra": 0, "pretrained_extra": 0}
    # Build a dict of pretrained word intervals by label for faster lookup (may be multiple same labels)
    # We'll match words by exact label and nearest temporal overlap.
    pr_word_intervals_by_label = defaultdict(list)
    for i in tier_pr_word.intervals:
        lbl = i.mark.strip()
        pr_word_intervals_by_label[lbl].append(i)

    # For each word interval in trained:
    for w_tr in tier_tr_word.intervals:
        lbl = w_tr.mark.strip()
        if not lbl:
            continue

        # find a pretrained word interval with same label that overlaps in time (choose the one with max overlap)
        candidates = pr_word_intervals_by_label.get(lbl, [])
        if not candidates:
            # no same-label word in pretrained; skip
            continue

        # pick candidate with largest overlap with trained word
        def overlap_len(a_start, a_end, b_start, b_end):
            return max(0.0, min(a_end, b_end) - max(a_start, b_start))

        best = None
        best_ov = 0.0
        for c in candidates:
            ov = overlap_len(w_tr.minTime, w_tr.maxTime, c.minTime, c.maxTime)
            if ov > best_ov:
                best_ov = ov
                best = c
        if best is None or best_ov == 0.0:
            # fallback: use first candidate
            best = candidates[0]

        w_pr = best

        # collect phones overlapping this word interval from both tiers
        phones_tr = phones_in_interval(tier_tr_t2, w_tr.minTime, w_tr.maxTime)
        phones_pr = phones_in_interval(tier_pr_t2, w_pr.minTime, w_pr.maxTime)

        # if lengths differ we will compare up to min length and record extras
        n_compare = min(len(phones_tr), len(phones_pr))
        unmatched_stats["trained_extra"] += max(0, len(phones_tr) - n_compare)
        unmatched_stats["pretrained_extra"] += max(0, len(phones_pr) - n_compare)

        for i in range(n_compare):
            p_tr = phones_tr[i]
            p_pr = phones_pr[i]

            # labels
            label_tr = p_tr.mark.strip() if p_tr.mark is not None else ""
            label_pr = p_pr.mark.strip() if p_pr.mark is not None else ""

            tone_tr = extract_tone_label(label_tr)
            tone_pr = extract_tone_label(label_pr)

            start_diff = abs(p_tr.minTime - p_pr.minTime)
            end_diff = abs(p_tr.maxTime - p_pr.maxTime)
            avg_diff = (start_diff + end_diff) / 2.0

            boundary_correct = avg_diff <= threshold
            label_correct = (tone_tr == tone_pr)

            results.append({
                "file": os.path.basename(trained_file),
                "word": lbl,
                "phone_tr": label_tr,
                "phone_pr": label_pr,
                "tone_tr": tone_tr,
                "tone_pr": tone_pr,
                "start_tr": p_tr.minTime,
                "end_tr": p_tr.maxTime,
                "start_pr": p_pr.minTime,
                "end_pr": p_pr.maxTime,
                "start_diff": start_diff,
                "end_diff": end_diff,
                "avg_diff": avg_diff,
                "boundary_correct": boundary_correct,
                "label_correct": label_correct
            })

    return {"results": results, "unmatched": unmatched_stats}

def analyze_all(trained_folder, pretrained_folder, threshold):
    all_rows = []
    file_errors = []
    unmatched_total = {"trained_extra": 0, "pretrained_extra": 0}

    for fname in os.listdir(trained_folder):
        if not fname.endswith(".TextGrid"):
            continue
        trained_path = os.path.join(trained_folder, fname)
        pretrained_path = os.path.join(pretrained_folder, fname)
        if not os.path.exists(pretrained_path):
            print(f"Pretrained missing for {fname}, skipping.")
            continue

        comp = compare_intervals(trained_path, pretrained_path, threshold)
        if "error" in comp:
            file_errors.append((fname, comp["error"]))
            continue

        for r in comp["results"]:
            all_rows.append(r)
        unmatched_total["trained_extra"] += comp["unmatched"]["trained_extra"]
        unmatched_total["pretrained_extra"] += comp["unmatched"]["pretrained_extra"]

    if not all_rows:
        print("No comparisons made (no matching files or no phone intervals).")
        return

    df = pd.DataFrame(all_rows)
    # Save detailed row-level results
    df.to_csv("boundary_and_label_comparison_detail.csv", index=False)
    print("Saved detailed results to 'boundary_and_label_comparison_detail.csv'.")

    # Overall stats
    overall_boundary_acc = df["boundary_correct"].mean() * 100
    overall_label_acc = df["label_correct"].mean() * 100

    print(f"\nOverall boundary accuracy (<= {threshold*1000:.0f} ms): {overall_boundary_acc:.2f}%")
    print(f"Overall label (tone) accuracy: {overall_label_acc:.2f}%")
    print(f"Unmatched (extra phones) across comparisons: {unmatched_total}")

    # Per-tone boundary accuracy & label accuracy
    # use pretrained tone as "true" tone
    tone_group = df.groupby("tone_pr").agg(
        total = ("tone_pr", "count"),
        boundary_correct = ("boundary_correct", "sum"),
        label_correct = ("label_correct", "sum")
    )
    tone_group["boundary_acc (%)"] = tone_group["boundary_correct"] / tone_group["total"] * 100
    tone_group["label_acc (%)"] = tone_group["label_correct"] / tone_group["total"] * 100
    tone_group = tone_group[["total", "boundary_acc (%)", "label_acc (%)"]].reset_index().rename(columns={"tone_pr":"true_tone"})
    print("\nPer-true-tone accuracy (true tone from pretrained):")
    print(tone_group.to_string(index=False))

    # Confusion matrix (true tone = tone_pr, predicted = tone_tr)
    conf = pd.crosstab(df["tone_pr"], df["tone_tr"], rownames=["true_tone"], colnames=["pred_tone"], margins=False)
    # Add totals and percent columns for each row
    conf_percent = conf.div(conf.sum(axis=1), axis=0).fillna(0) * 100
    conf.to_csv("tone_confusion_counts.csv")
    conf_percent.to_csv("tone_confusion_percent.csv")
    print("\nSaved confusion counts -> 'tone_confusion_counts.csv' and percent -> 'tone_confusion_percent.csv'.")

    # For each true tone, compute wrong-rate distribution
    wrong_details = []
    for true_tone, row in conf.iterrows():
        total = row.sum()
        if total == 0:
            continue
        for pred_tone, count in row.items():
            if pred_tone == true_tone:
                continue
            wrong_details.append({
                "true_tone": true_tone,
                "pred_tone": pred_tone,
                "count": int(count),
                "percent_of_true_tone": (count / total * 100) if total>0 else 0.0
            })
    wrong_df = pd.DataFrame(wrong_details)
    if not wrong_df.empty:
        wrong_df.to_csv("tone_wrong_distribution_per_true_tone.csv", index=False)
        print("Saved per-true-tone wrong-label distribution -> 'tone_wrong_distribution_per_true_tone.csv'.")

    # Print top confusions
    print("\nTop confusions (true_tone -> pred_tone : percent_of_true_tone):")
    if not wrong_df.empty:
        top_conf = wrong_df.sort_values("percent_of_true_tone", ascending=False).head(10)
        for _, r in top_conf.iterrows():
            print(f"  {r['true_tone']} -> {r['pred_tone']}: {r['percent_of_true_tone']:.2f}% ({r['count']})")
    else:
        print("  No mislabelings found.")

    # return dataframes for further use
    return {
        "detail_df": df,
        "tone_group": tone_group,
        "confusion_counts": conf,
        "confusion_percent": conf_percent,
        "wrong_df": wrong_df,
        "file_errors": file_errors
    }

if __name__ == "__main__":
    out = analyze_all(trained_folder, pretrained_folder, threshold)
