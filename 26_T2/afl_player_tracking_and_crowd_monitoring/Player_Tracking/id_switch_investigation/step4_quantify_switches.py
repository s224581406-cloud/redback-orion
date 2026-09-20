"""
Step 4: Turn the individual switch flags into an overall summary -
how common is this problem, really? This is the number you can
actually quote in your report/interview instead of a single anecdote.

Input:
  outputs/ocr_log.csv                    (from step1)
  outputs/switch_flags_with_cause.csv    (from step3)

Output:
  Printed summary + outputs/switch_summary.txt
"""

import csv
from collections import defaultdict

OCR_LOG_CSV = 'outputs/ocr_log.csv'
SWITCH_CSV = 'outputs/switch_flags_with_cause.csv'
SUMMARY_TXT = 'outputs/switch_summary.txt'

# Count total distinct tracks analysed
track_ids = set()
with open(OCR_LOG_CSV) as f:
    for row in csv.DictReader(f):
        track_ids.add(row['track_id'])
total_tracks = len(track_ids)

# Load switch flags (with cause info from step 3)
with open(SWITCH_CSV) as f:
    switches = list(csv.DictReader(f))

tracks_with_switch = set(s['track_id'] for s in switches)
n_switches = len(switches)
n_tracks_affected = len(tracks_with_switch)

# Break down by likely cause
cause_counts = defaultdict(int)
for s in switches:
    cause = s['likely_cause']
    if 'overlap' in cause:
        cause_counts['overlap with another player'] += 1
    elif 'jump' in cause:
        cause_counts['large position jump'] += 1
    else:
        cause_counts['unclear / possible OCR misread'] += 1

pct_affected = (n_tracks_affected / total_tracks * 100) if total_tracks else 0

summary_lines = [
    "=== Player Tracking ID Switch Investigation: Summary ===",
    "",
    f"Total tracks analysed:            {total_tracks}",
    f"Tracks with a likely ID switch:   {n_tracks_affected} ({pct_affected:.1f}%)",
    f"Total switch events found:        {n_switches}",
    "",
    "Breakdown by likely cause:",
]
for cause, count in cause_counts.items():
    summary_lines.append(f"  - {cause}: {count}")

summary_lines.append("")
summary_lines.append("Individual switches:")
for s in switches:
    summary_lines.append(
        f"  Track {s['track_id']}: '{s['reading_before']}' -> '{s['reading_after']}' "
        f"@ frame {s['switch_around_frame']} ({s['likely_cause']})"
    )

summary_text = '\n'.join(summary_lines)
print(summary_text)

with open(SUMMARY_TXT, 'w') as f:
    f.write(summary_text)

print(f"\nSaved summary to {SUMMARY_TXT}")
