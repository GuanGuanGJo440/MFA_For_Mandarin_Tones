print('Preprocessing WAVs...')

import soundfile as sf
import resampy
from pathlib import Path
import numpy as np

input_dir = Path("/Users/guanguangjo/Desktop/wav_Training_10_18_26")
output_dir = Path("/Users/guanguangjo/Desktop/wav_Training_10_18_26_output")
output_dir.mkdir(exist_ok=True)

min_samples = 1600  # ~0.1s at 16 kHz
skipped_files = []

for wav_file in input_dir.glob("*.wav"):
    data, sr = sf.read(wav_file)
    
    # Convert to mono first
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    
    # Skip very short files
    if len(data) < min_samples:
        skipped_files.append(wav_file.name)
        continue
    
    # Resample to 16 kHz if needed
    if sr != 16000:
        try:
            data = resampy.resample(data, sr, 16000)
            sr = 16000
        except ValueError as e:
            skipped_files.append(wav_file.name)
            print(f"Skipping {wav_file.name} due to resampling error: {e}")
            continue
    
    # Ensure 16-bit PCM
    data_int16 = np.int16(data / np.max(np.abs(data)) * 32767)
    
    sf.write(output_dir / wav_file.name, data_int16, sr, subtype='PCM_16')

print(f"Resampled WAVs saved to {output_dir}")
if skipped_files:
    print(f"Skipped {len(skipped_files)} files:", skipped_files)
