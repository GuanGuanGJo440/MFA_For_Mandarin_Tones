print('Comparing alignments...')

import os
from textgrid import TextGrid
import pandas as pd

# ===== CONFIG =====
trained_folder = "/Users/guanguangjo/Desktop/MFA_Align_Trained_Output"
pretrained_folder = "/Users/guanguangjo/Desktop/MFA_Align_Pretrained_Output"
threshold = 0.4  # 400 ms

# ==================

def extract_tier(textgrid, tier_name):
    """Return tier by name or None."""
    for tier in textgrid.tiers:
        if tier.name.lower() == tier_name.lower():
            return tier
    return None

def compare_intervals(file1, file2, threshold=0.4):
    """Compare boundaries in Tier 2 of two TextGrids."""
    tg1 = TextGrid.fromFile(file1)
    tg2 = TextGrid.fromFile(file2)

    tier1_word = extract_tier(tg1, "words")
    tier2_word = extract_tier(tg2, "words")
    tier1_phone = extract_tier(tg1, "phones") or extract_tier(tg1, "phone")
    tier2_phone = extract_tier(tg2, "phones") or extract_tier(tg2, "phone")

    if not (tier1_word and tier2_word and tier1_phone and tier2_phone):
        print(f"⚠️ Skipping {os.path.basename(file1)}: missing tier(s).")
        return []

    results = []

    # For each word interval in Tier 1
    for interval1 in tier1_word.intervals:
        label = interval1.mark.strip()
        if not label:
            continue

        # find same label in pretrained model
        interval2 = next((i for i in tier2_word.intervals if i.mark.strip() == label), None)
        if not interval2:
            continue

        # Phones inside this word interval
        phones1 = [p for p in tier1_phone.intervals if p.minTime >= interval1.minTime and p.maxTime <= interval1.maxTime]
        phones2 = [p for p in tier2_phone.intervals if p.minTime >= interval2.minTime and p.maxTime <= interval2.maxTime]

        # Match phones by order (assuming same segmentation order)
        for p1, p2 in zip(phones1, phones2):
            if not p1.mark or not p2.mark:
                continue

            start_diff = abs(p1.minTime - p2.minTime)
            end_diff = abs(p1.maxTime - p2.maxTime)
            avg_diff = (start_diff + end_diff) / 2

            correct = avg_diff <= threshold
            tone = ''.join([ch for ch in p1.mark if ch in "1234n"]) or "unknown"

            results.append({
                "word": label,
                "phone": p1.mark,
                "tone": tone,
                "avg_diff": avg_diff,
                "correct": correct
            })

    return results


def main():
    all_results = []

    # Compare matching files
    for fname in os.listdir(trained_folder):
        if not fname.endswith(".TextGrid"):
            continue
        trained_path = os.path.join(trained_folder, fname)
        pretrained_path = os.path.join(pretrained_folder, fname)
        if not os.path.exists(pretrained_path):
            continue

        file_results = compare_intervals(trained_path, pretrained_path, threshold)
        for r in file_results:
            r["file"] = fname
        all_results.extend(file_results)

    df = pd.DataFrame(all_results)
    if df.empty:
        print("No results found.")
        return

    # ===== Overall Accuracy =====
    overall_acc = df["correct"].mean() * 100

    # ===== Tone Accuracy =====
    tone_acc = df.groupby("tone")["correct"].mean() * 100
    tone_acc = tone_acc.reset_index().rename(columns={"correct": "accuracy (%)"})

    print(f"\n✅ Overall accuracy: {overall_acc:.2f}%")
    print("\n🎯 Tone-wise accuracy:")
    print(tone_acc)

    # Save to CSV
    df.to_csv("boundary_comparison_results.csv", index=False)
    print("\nResults saved to 'boundary_comparison_results.csv'.")

if __name__ == "__main__":
    main()
