# MFA_For_Mandarin_Tones

Adapting the Montreal Forced Aligner to align Mandarin lexical tones in Praat.

A complete workflow for aligning and training Mandarin acoustic models using [**Montreal Forced Aligner (MFA)**](https://montreal-forced-aligner.readthedocs.io/en/latest/).
This project provides Python scripts for preprocessing, TextGrid generation, tone-based modifications, and evaluation.

---

## 🧩 1. Environment Setup

### Install Anaconda or Miniconda

1. Go to [**anaconda.com/download**](https://www.anaconda.com/download?utm_source=anacondadocs&utm_medium=documentation&utm_campaign=download&utm_content=installmacgraphical) and register an account.
2. Download **Anaconda (Mac or Windows)** under *Distribution Installers*.
3. Double-click the downloaded file → click **Continue** to begin installation.
4. Read the license and click **Agree**.
5. Choose install location:
   * **Install for all users (recommended)** → `/opt/anaconda3`
   * or select a custom path.
6. Click **Install** and wait for it to finish.
7. When complete, click **Continue** → **Close**.

---

### Create MFA Environment

Open **Terminal** and run:

```bash
conda create -n aligner2.2.17 -c conda-forge montreal-forced-aligner=2.2.17 openfst=1.8.2 kaldi=5.5.1068
```

This creates an environment named **aligner2.2.17** for running **Montreal Forced Aligner v2.2.17**.

---

## 🧠 2. Setup Project

### Step 1: Clone Repository

```bash
git clone https://github.com/GuanGuanGJo440/MFA_For_Mandarin_Tones.git
cd MFA_For_Mandarin_Tones
```

---

### Step 2: Install Required Libraries

Inside your conda environment, install required packages:

```bash
pip install soundfile
pip install resampy
pip install textgrid
pip install pandas
```

✅ Make sure `soundfile`, `resampy`, `textgrid`, and `pandas` are all available.

---

### Step 3: Prepare Your Data

Place your files inside `/data`:

```
/data/
├── wavs/               ← raw WAV files (any sample rate, stereo)
├── transcripts.xlsx     ← Excel file (col A = filename, col B = text)
```

---

### Step 4: Preprocess WAVs

Convert all audio to **mono, 16kHz WAVs**:

```bash
python scripts/preprocess_wavs.py
```

Outputs will be saved to:

```
/data/wavs_preprocessed/
```

---

### Step 5: Create TextGrids

Generate TextGrids with the text from your Excel sheet:

```bash
python scripts/create_textgrids.py
```

Each TextGrid will have:

* **Tier name:** `words`
* **Content:** text label from the Excel file

Output directory:

```
/data/textgrids/
```

---

## 🎙️ 3. Run MFA Alignment

### Step 6: Activate MFA Environment

```bash
conda activate aligner2.2.17
```

### Step 7: Download Mandarin Models

```bash
mfa model download dictionary mandarin_taiwan_mfa
mfa model download acoustic mandarin_mfa
```

You can verify the downloads with:

```bash
mfa model inspect dictionary mandarin_taiwan_mfa
mfa model inspect acoustic mandarin_mfa
```

These correspond to:

* **Mandarin (Taiwan) MFA dictionary v2.0.0**
* **Mandarin MFA acoustic model v2.0.0a**

---

### Step 8: Align TextGrids with Pretrained Model

Place your preprocessed `.wav` and `.TextGrid` files into:

```
aligner_input/
```

Run:

```bash
mfa align --clean [corpus directory] [dictionary path] [acoustic model path] [output directory]
```

Move the resulting `.TextGrid` files from:

```
aligner_output/ → /data/textgrids/
```

Then, remove the old contents of `aligner_input/`.

---

## 🎵 4. Post-Alignment Processing

### Step 9: Switch Back to Base Conda Environment

```bash
conda activate base
```

### Step 10: Modify TextGrids (convert phones → tones)

```bash
python scripts/modify_textgrids.py
```

### Step 11: Generate Dictionary from TextGrids

```bash
python scripts/textgrids_to_dict.py
```

---

## 🧑‍🏫 5. Train Your Own Acoustic Model

### Step 12: Switch Back to MFA Environment

```bash
conda activate aligner2.2.17
```

### Step 13: Train Model

Place training data into:

```
training_corpus/
```

Run:

```bash
mfa train --clean [corpus directory] [dictionary path] [output directory]
```

Your trained acoustic model will be exported as a `.zip` file in the output directory.

---

## 🎧 6. Evaluate Model Accuracy

### Step 14: Generate Test Alignments

Place test data (`.wav` + `.TextGrid`) in:

```
aligner_input/
```

Run:

```bash
mfa align --clean [corpus directory] [dictionary path] [acoustic model path] [output directory]
```

Move results to:

```
/data/textgrids_test/
```

---

### Step 15: Compare Alignment Accuracy

Run:

```bash
python scripts/compare_alignments.py
```

This script compares boundary differences between your trained and pretrained MFA alignments.

---

## 🗂️ Project Structure

```
MFA_For_Mandarin_Tones/
├── data/
│   ├── wavs/
│   ├── wavs_preprocessed/
│   ├── textgrids/
│   ├── textgrids_modified/
│   ├── dict/
│   ├── transcripts.xlsx
│   ├── wavs_train/
│   ├── textgrids_train/
│   ├── wavs_test/
│   ├── textgrids_test/
├── scripts/
│   ├── preprocess_wavs.py
│   ├── create_textgrids.py
│   ├── modify_textgrids.py
│   ├── textgrids_to_dict.py
│   ├── compare_alignments.py
│   └── run_mfa_train.sh
├── rules.json
├── environment.yml
└── README.md
```



