print('Comparing alignments...')

import os
import re
from collections import defaultdict
from textgrid import TextGrid
from pathlib import Path
import pandas as pd

# ===================== CONFIG =====================
# === Path setup ===
base_dir = Path(__file__).resolve().parent.parent
trained_folder = base_dir / "data_test" / "output_textgrids_trained"
pretrained_folder = base_dir / "data_test" / "output_textgrids_pretrained_modified"
output_folder = base_dir / "data_test" / "accuracy_calculator"  # ✅ output folder
threshold = 0.1  # seconds (100 ms)
word_tier_name = "words"
tier2_candidates = ["phones", "phone", "tones", "tone"]
# ==================

os.makedirs(output_folder, exist_ok=True)

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
    m = re.search(r"([1234])", s)
    if m:
        return m.group(1)
    if re.search(r"\bn\b", s, re.IGNORECASE):
        return "n"
    if re.search(r"\b0\b", s):
        return "n"
    return "unknown"

def phones_in_interval(tier, interval_start, interval_end):
    """Return list of phone intervals overlapping with given word interval."""
    phones = [p for p in tier.intervals if p.maxTime > interval_start and p.minTime < interval_end]
    phones.sort(key=lambda x: x.minTime)
    return phones

def compare_intervals(trained_file, pretrained_file, threshold):
    tg_tr = TextGrid.fromFile(trained_file)
    tg_pr = TextGrid.fromFile(pretrained_file)

    tier_tr_word = extract_tier(tg_tr, word_tier_name)
    tier_pr_word = extract_tier(tg_pr, word_tier_name)
    if not (tier_tr_word and tier_pr_word):
        return {"error": f"missing word tier in {os.path.basename(trained_file)} or pretrained."}

    tier_tr_t2, _ = find_tier2(tg_tr)
    tier_pr_t2, _ = find_tier2(tg_pr)
    if not (tier_tr_t2 and tier_pr_t2):
        return {"error": f"missing Tier-2 (phones/tones) in {os.path.basename(trained_file)} or pretrained."}

    results = []
    unmatched_stats = {"trained_extra": 0, "pretrained_extra": 0}

    # group pretrained words by label
    pr_word_intervals_by_label = defaultdict(list)
    for i in tier_pr_word.intervals:
        lbl = i.mark.strip()
        pr_word_intervals_by_label[lbl].append(i)

    # compare
    for w_tr in tier_tr_word.intervals:
        lbl = w_tr.mark.strip()
        if not lbl:
            continue

        candidates = pr_word_intervals_by_label.get(lbl, [])
        if not candidates:
            continue

        def overlap_len(a_start, a_end, b_start, b_end):
            return max(0.0, min(a_end, b_end) - max(a_start, b_start))

        best = None
        best_ov = 0.0
        for c in candidates:
            ov = overlap_len(w_tr.minTime, w_tr.maxTime, c.minTime, c.maxTime)
            if ov > best_ov:
                best_ov = ov
                best = c
        if best is None:
            best = candidates[0]

        w_pr = best

        phones_tr = phones_in_interval(tier_tr_t2, w_tr.minTime, w_tr.maxTime)
        phones_pr = phones_in_interval(tier_pr_t2, w_pr.minTime, w_pr.maxTime)

        n_compare = min(len(phones_tr), len(phones_pr))
        unmatched_stats["trained_extra"] += max(0, len(phones_tr) - n_compare)
        unmatched_stats["pretrained_extra"] += max(0, len(phones_pr) - n_compare)

        for i in range(n_compare):
            p_tr = phones_tr[i]
            p_pr = phones_pr[i]

            label_tr = (p_tr.mark or "").strip()
            label_pr = (p_pr.mark or "").strip()

            tone_tr = extract_tone_label(label_tr)
            tone_pr = extract_tone_label(label_pr)

            # ✅ keep signed difference
            start_diff = p_tr.minTime - p_pr.minTime
            end_diff = p_tr.maxTime - p_pr.maxTime
            avg_diff = (start_diff + end_diff) / 2.0

            boundary_correct = abs(avg_diff) <= threshold
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
                "start_diff": start_diff,  # signed
                "end_diff": end_diff,      # signed
                "avg_diff": avg_diff,
                "boundary_correct": boundary_correct,
                "label_correct": label_correct
            })

    return {"results": results, "unmatched": unmatched_stats}

def analyze_all(trained_folder, pretrained_folder, threshold):
    all_rows = []
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
            print(comp["error"])
            continue

        all_rows.extend(comp["results"])
        unmatched_total["trained_extra"] += comp["unmatched"]["trained_extra"]
        unmatched_total["pretrained_extra"] += comp["unmatched"]["pretrained_extra"]

    if not all_rows:
        print("No comparisons made.")
        return

    df = pd.DataFrame(all_rows)
    df = df[(df["tone_pr"].isin(["1","2","3","4","n"])) & (df["tone_tr"].isin(["1","2","3","4","n"]))]

    # ✅ Save all results to output folder
    detail_path = os.path.join(output_folder, "boundary_and_label_comparison_detail.csv")
    df.to_csv(detail_path, index=False)
    print(f"Saved detailed results to '{detail_path}'.")

    overall_boundary_acc = df["boundary_correct"].mean() * 100
    overall_label_acc = df["label_correct"].mean() * 100
    print(f"\nOverall boundary accuracy (<= {threshold*1000:.0f} ms): {overall_boundary_acc:.2f}%")
    print(f"Overall label (tone) accuracy: {overall_label_acc:.2f}%")
    print(f"Unmatched (extra phones): {unmatched_total}")

    # ✅ Count boundaries before/after
    before_count = ((df["start_diff"] < 0) | (df["end_diff"] < 0)).sum()
    after_count = ((df["start_diff"] > 0) | (df["end_diff"] > 0)).sum()
    print(f"\nBoundary timing direction:")
    print(f"  Earlier than pretrained (negative diff): {before_count}")
    print(f"  Later than pretrained (positive diff):  {after_count}")

    # per-tone stats
    tone_group = df.groupby("tone_pr").agg(
        total=("tone_pr", "count"),
        boundary_correct=("boundary_correct", "sum"),
        label_correct=("label_correct", "sum")
    )
    tone_group["boundary_acc (%)"] = tone_group["boundary_correct"] / tone_group["total"] * 100
    tone_group["label_acc (%)"] = tone_group["label_correct"] / tone_group["total"] * 100
    tone_group = tone_group[["total", "boundary_acc (%)", "label_acc (%)"]].reset_index()
    # === Print and save per-true-tone accuracy ===
    print("\nPer-true-tone accuracy (true tone from pretrained):")
    print(tone_group.to_string(index=False))
    tone_acc_path = os.path.join(output_folder, "tone_accuracy_summary.csv")
    tone_group.to_csv(tone_acc_path, index=False)
    print(f"\nSaved tone accuracy summary to '{tone_acc_path}'.")

    # confusion matrix
    conf = pd.crosstab(df["tone_pr"], df["tone_tr"], rownames=["true_tone"], colnames=["pred_tone"])
    conf_percent = conf.div(conf.sum(axis=1), axis=0).fillna(0) * 100
    conf.to_csv(os.path.join(output_folder, "tone_confusion_counts.csv"))
    conf_percent.to_csv(os.path.join(output_folder, "tone_confusion_percent.csv"))

    print("\nSaved confusion counts and percentages.")

if __name__ == "__main__":
    analyze_all(trained_folder, pretrained_folder, threshold)
