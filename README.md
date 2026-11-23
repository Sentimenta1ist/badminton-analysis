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
- `python -m bda report --session SESSION_DIR [--history metrics.csv]` — one self-contained `report.html` (images inlined as base64, inline SVG charts, light/dark, one column on phones).
- `python -m bda progress --root BRAIN/badminton` — `progress.html` next to `sessions/`: trends of every metric, best frames per session, links to each `report.html`.

## Session report: notes.json
`report` reads `metrics.json`, `events.json`, `img/*.jpg` and history from the session folder, plus the text from
`notes.json`. The previous session (folder `sessions/<earlier date>` next to this one) supplies last time's tasks and
"before / after" frames.

```json
{
 "date": "2026-11-29", "title": "…", "opponent": "…", "score": "21:17", "cameras": "back + side, 1080p60",
 "duration": "31:20", "break_t": 1260, "lede": "…",
 "main": ["**Bold** lead, then text", "…"],
 "sections": [{"title": "1. Legs", "text": ["…"], "fix": "…",
   "frames": [{"file": "img/p_low1.jpg", "t": 279.0, "verdict": "good|bad|warn",
               "kind": "low", "kind_ru": "Низкая готовность", "short": "низкая готовность", "best": true,
               "caption": "what is wrong / right", "fix": "how to fix (bad frames)", "wide": false}]}],
 "tasks": [{"what": "…", "metric": "neutral_high_share", "now": 76.5, "target": 50, "op": "<="}],
 "drills": ["…"], "limits": ["…"], "links": [{"title": "…", "url": "…"}]
}
```
- `kind` only on the main example of each type (`tall`, `low`, `oh_good`, `oh_bad`, `lunge_good`, `lunge_bad`,
  `side_lunge`, `side_trunk`): frames with the same `kind` in consecutive sessions are shown as "before / after".
- `best: true` marks frames for `progress.html` (otherwise 2 good + 2 bad). `wide: true` for strips/montages.
- `skip_metrics`: metrics the camera angle makes meaningless (e.g. a corner camera: shoulder turn, stance width,
  lunge lean, court position). They are hidden in the report; pass the same list to `compare.append(..., skip=...)`
  so they never enter the history.
- Text supports `**bold**` and `` `code` ``.

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
