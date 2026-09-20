"""
Step 2: Look through the per-frame OCR log (from Step 1) and detect
"switch points" - places where a track's jersey number reading
changes and STAYS changed, suggesting the tracker lost/swapped the
player, rather than a single noisy misread.

Rule used:
  - Only trust readings with confidence > MIN_CONFIDENCE
  - A "stretch" is a run of consecutive confident readings of the
    same number
  - If a track has two or more stretches of at least MIN_STRETCH
    frames, with DIFFERENT numbers, that's flagged as a likely switch

Input:  outputs/ocr_log.csv (produced by step1_log_all_tracks.py)
Output: outputs/switch_flags.csv
"""

import csv
from collections import defaultdict
from itertools import groupby

INPUT_CSV = 'outputs/ocr_log.csv'
OUTPUT_CSV = 'outputs/switch_flags.csv'

MIN_CONFIDENCE = 0.3   # ignore low-confidence noise
MIN_STRETCH = 8        # need at least this many consecutive frames to count as a real "stretch"

# Load and group rows by track_id
tracks = defaultdict(list)
with open(INPUT_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['frame'] = int(row['frame'])
        row['confidence'] = float(row['confidence'])
        tracks[row['track_id']].append(row)

flags = []

for track_id, rows in tracks.items():
    rows.sort(key=lambda r: r['frame'])

    # Keep only confident, non-empty readings, in frame order
    confident = [r for r in rows if r['reading'] and r['confidence'] > MIN_CONFIDENCE]
    if not confident:
        continue

    # Group consecutive frames with the SAME reading into "stretches"
    stretches = []
    current_reading = None
    current_start = None
    current_len = 0
    prev_frame = None

    for r in confident:
        same_as_last = (r['reading'] == current_reading) and (
            prev_frame is None or r['frame'] - prev_frame <= 3  # allow small gaps
        )
        if same_as_last:
            current_len += 1
        else:
            if current_reading is not None and current_len >= MIN_STRETCH:
                stretches.append((current_reading, current_start, prev_frame, current_len))
            current_reading = r['reading']
            current_start = r['frame']
            current_len = 1
        prev_frame = r['frame']

    if current_reading is not None and current_len >= MIN_STRETCH:
        stretches.append((current_reading, current_start, prev_frame, current_len))

    # If there are 2+ stretches with DIFFERENT readings, flag as a likely switch
    distinct_readings = set(s[0] for s in stretches)
    if len(stretches) >= 2 and len(distinct_readings) >= 2:
        for i in range(len(stretches) - 1):
            reading_a, start_a, end_a, len_a = stretches[i]
            reading_b, start_b, end_b, len_b = stretches[i + 1]
            if reading_a != reading_b:
                flags.append({
                    'track_id': track_id,
                    'reading_before': reading_a,
                    'frames_before': f"{start_a}-{end_a} ({len_a} frames)",
                    'reading_after': reading_b,
                    'frames_after': f"{start_b}-{end_b} ({len_b} frames)",
                    'switch_around_frame': end_a  # last confident frame before the change
                })

with open(OUTPUT_CSV, 'w', newline='') as f:
    fieldnames = ['track_id', 'reading_before', 'frames_before',
                  'reading_after', 'frames_after', 'switch_around_frame']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(flags)

print(f"Checked {len(tracks)} tracks.")
print(f"Found {len(flags)} likely ID switch(es). Saved to {OUTPUT_CSV}")
for f_row in flags:
    print(f"  Track {f_row['track_id']}: '{f_row['reading_before']}' -> '{f_row['reading_after']}' "
          f"around frame {f_row['switch_around_frame']}")
