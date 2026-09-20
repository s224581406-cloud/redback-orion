"""
Step 1: Run OCR across EVERY track (not just one), and save the full
frame-by-frame reading history for each track to a CSV.

This builds on your existing single-track OCR script, but instead of
only keeping the final majority-vote answer, it keeps every individual
frame's reading so we can later look for the exact point a track's
jersey number reading changes.

Input expected:  outputs/jersey_crops/track_<id>/frame_<n>.jpg
Output produced: outputs/ocr_log.csv
"""

import easyocr
import cv2
import glob
import os
import csv

reader = easyocr.Reader(['en'], gpu=False)

TRACK_DIRS = sorted(glob.glob('outputs/jersey_crops/track_*'))
OUTPUT_CSV = 'outputs/ocr_log.csv'

rows = []

for track_dir in TRACK_DIRS:
    track_id = os.path.basename(track_dir).replace('track_', '')
    image_paths = sorted(glob.glob(f'{track_dir}/*.jpg'))

    print(f"Track {track_id}: {len(image_paths)} frames")

    for path in image_paths:
        frame_name = os.path.basename(path)
        # frame number is expected in the filename, e.g. frame_878.jpg
        frame_num = ''.join(filter(str.isdigit, frame_name)) or '0'

        img = cv2.imread(path)
        if img is None:
            continue

        h, w = img.shape[:2]
        upscaled = cv2.resize(img, None, fx=min(3, 400/max(h, w)), fy=min(3, 400/max(h, w)), interpolation=cv2.INTER_CUBIC)
        results = reader.readtext(upscaled, allowlist='0123456789')

        if results:
            best = max(results, key=lambda r: r[2])
            text, conf = best[1], best[2]
        else:
            text, conf = '', 0.0

        rows.append({
            'track_id': track_id,
            'frame': int(frame_num),
            'reading': text,
            'confidence': round(conf, 3)
        })

# Save everything to one CSV, sorted by track then frame order
rows.sort(key=lambda r: (r['track_id'], r['frame']))

with open(OUTPUT_CSV, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['track_id', 'frame', 'reading', 'confidence'])
    writer.writeheader()
    writer.writerows(rows)

print(f"\nDone. Saved {len(rows)} frame readings across {len(TRACK_DIRS)} tracks to {OUTPUT_CSV}")
