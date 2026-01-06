# MFA_For_Mandarin_Tones

This project is designed to assist in generating **acoustic models for Mandarin tone alignment**.

It helps users create or modify **TextGrid** files within a speech corpus for tone-based alignment using the **Montreal Forced Aligner (MFA)** framework.

---

## 📦 Requirements

Before running the scripts, users need to prepare:

1. **Speech samples** in `.wav` format
2. **An Excel file** that records:
    - **Column 1:** File name of each wave file
    - **Column 2:** Corresponding text transcription

---

## ⚙️ Environment Setup

### 1. Install Anaconda

Download and install **Anaconda** (or **Miniconda**) from the official website:

[👉 https://www.anaconda.com/download](https://www.anaconda.com/download?utm_source=anacondadocs&utm_medium=documentation&utm_campaign=download&utm_content=installmacgraphical)

Follow these steps:

1. Register and click **Download for Mac** or the Windows installer under *Distribution Installers*.
2. Double-click the installer and click **Continue**.
3. View the *Read Me* and click **Continue**.
4. Read and agree to the [Anaconda Terms of Service](https://anaconda.com/legal).
5. Choose installation type:
    - **For all users (recommended)** → installs in `/opt/anaconda3`
    - **Custom disk location** → choose a different path
6. Click **Install** and wait for the process to complete.
7. Click **Continue**, then **Close**.

---

### 2. Create the MFA environment

Open your **terminal** and run:

```bash
conda create -n aligner2.2.17 -c conda-forge montreal-forced-aligner=2.2.17 openfst=1.8.2 kaldi=5.5.1068

```

This creates a new environment called **aligner2.2.17**, which includes **Montreal Forced Aligner (v2.2.17)** and its dependencies.

Then, open **two terminal windows**:

- One for your base environment
- One for the MFA environment (activate it with:)

```bash
conda activate aligner2.2.17

```

---

### 3. Download pretrained MFA models

In the `aligner2.2.17` environment, run:

```bash
mfa model download dictionary mandarin_taiwan_mfa
mfa model download acoustic mandarin_mfa

```

This downloads:

- **Mandarin (Taiwan) MFA Dictionary v3.0.0**
- **Mandarin MFA Acoustic Model v2.0.0a**

Verify the installations:

```bash
mfa model inspect dictionary mandarin_taiwan_mfa
mfa model inspect acoustic mandarin_mfa

```

If no errors appear, you are ready to proceed.

---

## 🧠 Training Acoustic Models

### Step 1: Clone this repository

```bash
git clone https://github.com/GuanGuanGJo440/MFA_For_Mandarin_Tones.git
cd MFA_For_Mandarin_Tones

```

---

### Step 2: Install required libraries

In your **conda (base) environment**, install dependencies:

```bash
pip install soundfile
pip install resampy
pip install textgrid
pip install pandas

```

Make sure your environment includes:

- `soundfile`
- `resampy`
- `textgrid`
- `pandas`

---

### Step 3: Prepare input data

Place your data under the `/data_train` folder:

- **Wave files** → `/data_train/wavs/`
- **Excel file** → `/data_train/`

---

### Step 4: Preprocess wav files

Ensure all `.wav` files are mono and 16 kHz:

```bash
python scripts/preprocess_wavs.py

```

Output files will be saved in `/data_train/wavs_preprocessed/`.

---

### Step 5: Create TextGrids

Generate initial TextGrids with word-level annotations:

```bash
python scripts/create_textgrids.py

```

Each `.TextGrid` will contain a **tier named “words”** with corresponding text.

---

### Step 6: Create a prealigned corpus

```bash
python scripts/create_prealigned_corpus.py

```

This moves the generated TextGrids into `/data_train/aligner_input/`

and copies preprocessed `.wav` files into the same folder.

---

### Step 7: (In MFA environment) Align using pretrained model

```bash
mfa align --clean [corpus directory] [dictionary path] [acoustic path] [output directory]

```

**Example paths:**

- `corpus directory` → `/data_train/aligner_input`
- `dictionary path` → MFA pretrained dictionary `.dict` file
- `acoustic path` → MFA pretrained acoustic `.zip` file
- `output directory` → `/data_train/textgrids_modified`

---

### Step 8: Modify TextGrids for tone alignment

Convert phoneme-based alignments to **tone-based tiers**:

```bash
python scripts/modify_textgrids.py

```

---

### Step 9: (Optional) Generate dictionary from TextGrids

```bash
python scripts/textgrids_to_dict.py

```

This creates a custom dictionary in `/data_train/dict/`.

---

### Step 10: Create training corpus

Combine preprocessed wavs and modified TextGrids:

```bash
python scripts/create_training_corpus.py

```

The result will be in `/data_train/training_corpus/`.

---

### Step 11: Train the acoustic model (MFA environment)

Prepare your corpus and dictionary, then run:

```bash
mfa train --clean --config_path [configuration path] [corpus directory] [dictionary path] [output directory]

```

**Example paths:**

- `configuration path` → `/models/trained_model/training_config/*.yaml`
- `corpus directory` → `/data_train/training_corpus/`
- `dictionary path` → `/data_train/dict/` *(or pretrained dictionary)*
- `output directory` → your output `.zip` model file (e.g. `my_acoustic_model.zip`)

The trained acoustic model will be saved as a `.zip` file.

---

## 🧪 Testing Phase

### Step 12: Test the trained model (MFA environment)

Place your test files in `/data_test/testing_corpus/`.

Then run:

```bash
mfa align --clean [corpus directory] [dictionary path] [acoustic path] [output directory]

```

**Example paths:**

- `corpus directory` → `/data_test/testing_corpus/`
- `dictionary path` → your trained or pretrained dictionary
- `acoustic path` → trained model `.zip`
- `output directory` → `/data_test/output_textgrids_trained/`

---

### Step 13: Test the pretrained model

```bash
mfa align --clean [corpus directory] [dictionary path] [acoustic path] [output directory]

```

**Example paths:**

- `corpus directory` → `/data_test/testing_corpus/`
- `dictionary path` → pretrained dictionary
- `acoustic path` → pretrained acoustic model
- `output directory` → `/data_test/output_textgrids_pretrained_original/`

---

### Step 14: Preprocess before tone comparison

Run:

```bash
python scripts/modify_textgrids_before_tone_alignment.py

```

---

### Step 15: Calculate accuracy

Run the evaluation script:

```bash
python scripts/compare_alignments.py

```

Results will be saved in `/data_test/accuracy_calculator/`.

---

## 🧾 Summary of Key Directories

| Folder | Description |
| --- | --- |
| `data_train/wavs/` | Original speech samples |
| `data_train/wavs_preprocessed/` | Preprocessed mono 16 kHz wavs |
| `data_train/aligner_input/` | Input for MFA alignment |
| `data_train/textgrids_modified/` | TextGrids after alignment |
| `data_train/training_corpus/` | Data for training custom acoustic models |
| `data_test/testing_corpus/` | Test set |
| `data_test/output_textgrids_trained/` | Output aligned by trained model |
| `data_test/output_textgrids_pretrained_original/` | Output aligned by pretrained model |
| `data_test/accuracy_calculator/` | Accuracy results |

---

## 📚 References

- [Montreal Forced Aligner Documentation](https://montreal-forced-aligner.readthedocs.io/)
- [Mandarin MFA Models](https://mfa-models.readthedocs.io/en/latest/)