"""Compare a session's metrics with history (metrics.csv in the brain domain).

metrics.csv columns: date,session,metric,value,version
"""
import csv, os
from .metrics_def import METRICS


def load_history(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def append(path, date, session, metrics):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["date", "session", "metric", "value", "version"])
        for k, v in metrics.items():
            if v is None or k not in METRICS:
                continue
            w.writerow([date, session, k, round(float(v), 3), METRICS[k]["version"]])


def table(history, date, metrics, tol=None):
    """Markdown table: metric | previous | now | delta | verdict. Verdict uses the metric direction."""
    tol = tol or {}
    prev, nxt = {}, {}
    for row in history:
        k = row["metric"]
        if row["date"] < date and (k not in prev or row["date"] > prev[k]["date"]):
            prev[k] = row
        if row["date"] > date and (k not in nxt or row["date"] < nxt[k]["date"]):
            nxt[k] = row
    # older video added after newer ones: compare it with the next session instead ("then -> later")
    reverse = not prev and bool(nxt)
    if reverse:
        prev = nxt
    head = "| Метрика | Позже | Эта сессия (раньше) | Δ (позже − раньше) | Итог к позже |" if reverse else "| Метрика | Было | Стало | Δ | Итог |"
    lines = [head, "|---|---|---|---|---|"]
    for k, d in METRICS.items():
        v = metrics.get(k)
        if v is None:
            continue
        p = prev.get(k)
        if p is None or int(p["version"]) != d["version"]:
            lines.append(f"| {d['ru']} | — | {v:.1f} | | первая точка |"); continue
        pv = float(p["value"]); delta = (pv - v) if reverse else (v - pv)
        t = tol.get(k, 3.0 if d["unit"] == "%" else 0.05 * max(abs(pv), 1e-6))
        if d["direction"] == "info" or abs(delta) <= t:
            verdict = "≈ так же" if abs(delta) <= t else "инфо"
        else:
            better = (delta < 0) == (d["direction"] == "lower")
            verdict = "лучше" if better else "хуже"
        lines.append(f"| {d['ru']} | {pv:.1f} ({p['date']}) | {v:.1f} | {delta:+.1f} | {verdict} |")
    return "\n".join(lines)
