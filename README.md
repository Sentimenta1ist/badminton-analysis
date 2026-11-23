# badminton-analysis

Turn match videos (back camera + optional 45° side camera) into comparable numbers about
footwork, overhead technique and lunges, plus annotated frames. Built for tracking one player's
progress week to week; no video is stored, only keypoints, metrics and a few frames.

## Install (macOS, Apple Silicon)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # also needs ffmpeg: brew install ffmpeg
```
The first run downloads the pose model (`yolo11l-pose.pt`, ~50 MB) from the Ultralytics GitHub releases.

## Run

```bash
python -m bda run --back back.mp4 --side side.mp4 --out work/2026-11-29 --date 2026-11-29 \
  --history ~/dev/brain/badminton/metrics.csv [--start 190] [--end 2100] [--break-t 1260]
```
Outputs in `--out`:

| file | what |
|---|---|
| `keypoints_back.json.gz`, `keypoints_side.json.gz` | 17 COCO keypoints per frame for every person (no pixels) |
| `rallies.json` | detected rallies `[[start, end], …]`, edit by hand and run `recompute` |
| `metrics.json` | session metrics (see `bda/metrics_def.py`) |
| `events.json` | overheads, lunges, per-rally stats with timestamps |
| `compare.md` | metrics vs the previous session from `--history` |
| `check_timeline.jpg` | one image to verify rally detection (red border = in rally) |
| `check_frames.jpg` + `frames/` | auto-picked example frames with skeleton |

Other commands:
- `python -m bda recompute --out DIR --date D [--history CSV]` — metrics again from saved keypoints (after editing `rallies.json` or changing a formula).
- `python -m bda frames --out DIR --video V --times "84.5:label;220.8:label" [--camera side --offset S]` — render chosen moments.

## Method (short)
- Pose: Ultralytics YOLO11 pose, 15 fps by default, the analysed player = tallest person, tracked for continuity.
- Lengths are normalised by torso length, so distance to the camera does not matter.
- "High between shots": hip-to-ankle height ≥ 94% of the player's own walking height (back camera).
- Overhead: right wrist above head; side-on = shoulder width shrinks below 50% of normal; left arm up = left wrist above left shoulder in the 0.6 s before.
- Lunge: feet wider than 1.1 torso and hips below 85% of walking height; trunk lean measured in the image plane.
- Side camera (45° from the net post): knee angle and forward trunk lean, which the back camera cannot see.
- Two cameras are synced by audio cross-correlation (clap at the start helps).

Limits: single-person tracking assumes the analysed player is nearest to the back camera; rally detection
is heuristic (check `check_timeline.jpg`); angles from a 45° camera are consistent session to session but
not true anatomical angles.
