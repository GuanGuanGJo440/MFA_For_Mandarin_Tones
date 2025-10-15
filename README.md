# MFA_For_Mandarin_Tones

Adapting the Montreal Forced Aligner to align Mandarin lexical tones in Praat.

# Step 1: Clone repo
git clone https://github.com/GuanGuanGJo440/MFA_For_Mandarin_Tones.git
cd MFA_For_Mandarin_Tones

# Step 2: Activate your environment (must include soundfile, resampy, textgrid, pandas)
conda activate base  # example

# Step 3: Put raw wav files and Excel in /data
# e.g., /data/wavs/*.wav and /data/Test_SoundRecogntion.xlsx

# Step 4: Run preprocessing
python scripts/preprocess_wavs.py

# Step 5: Create TextGrids
python scripts/create_textgrids.py
