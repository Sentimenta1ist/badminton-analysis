"""Rally detection from the analysed player's activity (no audio, no shuttle tracking).

Activity per second = foot travel (torso units) + wide stance + low athletic stance + overhead arm.
Picking the shuttle up (low hips, narrow feet) is not counted. Segments are smoothed, short gaps merged.
The result is written to rallies.json and can be edited by hand (Claude checks it on the timeline strip).
"""
import numpy as np


def activity(rows):
    T = np.array([r["t"] for r in rows])
    if len(T) == 0:
        return np.array([]), np.array([])
    legh = np.array([r["legh"] for r in rows]); st = np.array([r["stance"] for r in rows])
    tor = np.array([r["torso"] for r in rows])
    fx = np.array([r["foot_x"] for r in rows]) / tor; fy = np.array([r["foot_y"] for r in rows]) / tor
    rwa = np.array([r["rw_above"] if r["rw_above"] is not None else -9 for r in rows])
    hi = np.percentile(legh, 75)
    secs = np.arange(int(T.min()), int(T.max()) + 1)
    act = np.zeros(len(secs))
    for i, s in enumerate(secs):
        m = (T >= s) & (T < s + 1)
        if m.sum() < 3:
            continue
        sp = np.sum(np.hypot(np.diff(fx[m]), np.diff(fy[m])))
        athletic = (legh[m] < 0.85 * hi) & (st[m] > 0.6)
        act[i] = sp + 3 * np.mean(st[m] > 1.0) + 3 * np.mean(athletic) + 3 * float(np.any(rwa[m] > 0.25))
    return secs, act


def detect(rows, thr=None, smooth=3, min_len=3.0, merge_gap=2.0, pad=0.5):
    """thr=None: 3.5 at 10 fps, scaled with the analysis fps (keypoint jitter adds foot travel per extra frame)."""
    secs, act = activity(rows)
    if len(secs) == 0:
        return []
    if thr is None:
        T = np.array([r["t"] for r in rows])
        fps = (len(T) - 1) / max(T[-1] - T[0], 1e-6) if len(T) > 1 else 10.0
        thr = 3.5 * max(fps, 10.0) / 10.0
    sm = np.convolve(act, np.ones(smooth) / smooth, "same")
    on = sm > thr
    segs, start = [], None
    for s, v in zip(secs, on):
        if v and start is None:
            start = s
        if not v and start is not None:
            segs.append([float(start), float(s)]); start = None
    if start is not None:
        segs.append([float(start), float(secs[-1] + 1)])
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] <= merge_gap:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [[max(0.0, a - pad), b + pad] for a, b in merged if b - a >= min_len]


def label(t, rallies):
    for i, (a, b) in enumerate(rallies):
        if a <= t <= b:
            return i + 1
    return 0
