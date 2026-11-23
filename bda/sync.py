"""Find the time offset between two cameras from the audio (clap at the start, or rally sounds).

Returns offset_side = how many seconds to ADD to side-camera time to get back-camera time.
"""
import subprocess, numpy as np


def _env(video, seconds=120, sr=8000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-t", str(seconds), "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float)
    hop = sr // 100                       # 10 ms
    x = np.abs(np.diff(x))                # crude high-pass: claps/hits are sharp
    e = np.array([x[i:i + hop].mean() for i in range(0, len(x) - hop, hop)])
    e = (e - np.median(e)) / (np.std(e) + 1e-9)
    return np.clip(e, 0, None)


def offset(back, side, seconds=120, max_shift=60):
    a, b = _env(back, seconds), _env(side, seconds)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    best, best_lag = -1, 0
    lim = int(max_shift * 100)
    for lag in range(-lim, lim + 1):
        if lag >= 0:
            s = float(np.dot(a[lag:], b[:n - lag]))
        else:
            s = float(np.dot(a[:n + lag], b[-lag:]))
        if s > best:
            best, best_lag = s, lag
    # a[t+lag] ~ b[t]  ->  back_time = side_time + lag/100
    return best_lag / 100.0
