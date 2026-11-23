# badminton-analysis — notes for Claude

- Used by the `/badminton` command in the brain repo (`~/dev/brain/.claude/commands/badminton.md`). The brain
  domain `badminton/` holds the history (`metrics.csv`) and per-session folders; this repo holds only code.
- Never commit videos, model weights or personal data. Work dirs go to `work/` (gitignored).
- Metric definitions live only in `bda/metrics_def.py`. Changing a formula = bump its `version`, then run
  `recompute` for every saved session in brain so history stays comparable.
- Token budget: look at `check_timeline.jpg` and `check_frames.jpg` (2 images), plus at most a few extra
  frames rendered with `frames`. Everything else is read from JSON.
- Commits: short message, no Claude attribution lines.
