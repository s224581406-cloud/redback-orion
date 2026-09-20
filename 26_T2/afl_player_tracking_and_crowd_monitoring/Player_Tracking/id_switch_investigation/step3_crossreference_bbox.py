"""
Step 3: For every likely switch flagged in Step 2, look at the
tracking CSV's bounding boxes around that moment. This checks WHY
the switch happened - did the box jump an unusually large distance,
or overlap heavily with another player's box right before the
reading changed?

Input:
  outputs/switch_flags.csv          (from step2_detect_switches.py)
  <tracking_csv>                    (your track_video.py output:
                                      frame, track_id, class, confidence,
                                      x1, y1, x2, y2)

Output:
  outputs/switch_flags_with_cause.csv
"""

import csv
from collections import defaultdict

SWITCH_FLAGS_CSV = 'outputs/switch_flags.csv'
TRACKING_CSV = 'outputs/clip2_player_ref_best.csv'
OUTPUT_CSV = 'outputs/switch_flags_with_cause.csv'

WINDOW = 5              # how many frames before/after to check
OVERLAP_JUMP_PX = 80    # a box centre moving more than this many px in one frame looks suspicious


def box_centre(x1, y1, x2, y2):
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def iou(box1, box2):
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    intersection = (x_right - x_left) * (y_bottom - y_top)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    return intersection / (area1 + area2 - intersection)


# Load tracking data, grouped by frame, then by track_id
frames = defaultdict(dict)  # frames[frame_num][track_id] = (x1,y1,x2,y2)
with open(TRACKING_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        frame = int(row['frame'])
        tid = row['track_id']
        box = tuple(float(row[k]) for k in ('x1', 'y1', 'x2', 'y2'))
        frames[frame][tid] = box

# Load flagged switches from Step 2
with open(SWITCH_FLAGS_CSV) as f:
    switches = list(csv.DictReader(f))

results = []

for sw in switches:
    tid = sw['track_id']
    switch_frame = int(sw['switch_around_frame'])

    max_jump = 0.0
    max_overlap_with_other = 0.0
    overlapping_track = None

    for offset in range(-WINDOW, WINDOW + 1):
        f_num = switch_frame + offset
        if f_num not in frames or tid not in frames[f_num]:
            continue

        this_box = frames[f_num][tid]

        # Check jump vs previous frame of the SAME track
        prev_box = frames.get(f_num - 1, {}).get(tid)
        if prev_box:
            jump = distance(box_centre(*this_box), box_centre(*prev_box))
            max_jump = max(max_jump, jump)

        # Check overlap with any OTHER track in the same frame
        for other_tid, other_box in frames[f_num].items():
            if other_tid == tid:
                continue
            ov = iou(this_box, other_box)
            if ov > max_overlap_with_other:
                max_overlap_with_other = ov
                overlapping_track = other_tid

    likely_cause = []
    if max_jump > OVERLAP_JUMP_PX:
        likely_cause.append(f"large position jump ({max_jump:.0f}px)")
    if max_overlap_with_other > 0.3:
        likely_cause.append(f"overlap with track {overlapping_track} (IoU={max_overlap_with_other:.2f})")
    if not likely_cause:
        likely_cause.append("no clear box-level cause found - may be an OCR misread, not a real switch")

    sw['max_position_jump_px'] = round(max_jump, 1)
    sw['max_overlap_iou'] = round(max_overlap_with_other, 3)
    sw['overlapping_track'] = overlapping_track or ''
    sw['likely_cause'] = '; '.join(likely_cause)
    results.append(sw)

fieldnames = list(results[0].keys()) if results else []
with open(OUTPUT_CSV, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print(f"Cross-referenced {len(results)} switch(es) against bounding box data.")
print(f"Saved to {OUTPUT_CSV}")
for r in results:
    print(f"  Track {r['track_id']} switch @ frame {r['switch_around_frame']}: {r['likely_cause']}")
