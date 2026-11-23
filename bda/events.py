"""Turn per-frame rows into events (overheads, lunges) and session metrics."""
import numpy as np
from .rallies import label


def _arr(rows, k):
    return np.array([np.nan if r.get(k) is None else r[k] for r in rows], float)


def _group(idx, T, gap):
    groups = []
    for i in idx:
        if groups and T[i] - T[groups[-1][-1]] <= gap:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def back_metrics(rows, rallies, break_t=None):
    """Metrics from the back camera. break_t: time of the interval at 11 (for before/after split)."""
    T = np.array([r["t"] for r in rows])
    rally = np.array([label(t, rallies) for t in T])
    legh, stance, shw, X = _arr(rows, "legh"), _arr(rows, "stance"), _arr(rows, "shw"), _arr(rows, "X")
    rwa, lwa, lean, footy, torso = _arr(rows, "rw_above"), _arr(rows, "lw_above"), _arr(rows, "lean"), _arr(rows, "foot_y"), _arr(rows, "torso")
    idle = (rally == 0) & (stance < 0.6)
    base_leg = float(np.nanmedian(legh[idle])) if idle.sum() > 20 else float(np.nanpercentile(legh, 75))
    base_shw = float(np.nanmedian(shw[idle])) if idle.sum() > 20 else float(np.nanmedian(shw))

    # overheads: right wrist clearly above the head during a rally
    overheads = []
    for g in _group(np.where(rwa > 0.25)[0], T, 0.35):
        p = max(g, key=lambda i: rwa[i]); tp = T[p]
        if rally[p] == 0:
            continue
        pre = (T >= tp - 0.8) & (T <= tp - 0.05); prew = (T >= tp - 0.6) & (T <= tp)
        before = (T >= tp - 1.3) & (T <= tp - 0.7)
        side_on = float(np.nanmin(shw[pre]) / base_shw) if pre.any() else None
        left = float(np.nanmax(lwa[prew])) if prew.any() and not np.all(np.isnan(lwa[prew])) else None
        jump = None
        if before.any():
            near = (T >= tp - 0.15) & (T <= tp + 0.15)
            jump = bool(np.nanmin(footy[near]) < np.nanmedian(footy[before]) - 0.25 * np.nanmedian(torso[before]))
        overheads.append(dict(t=float(tp), rally=int(rally[p]), reach=float(rwa[p]), side_on=side_on, left_up=left, jump=jump,
                              turned=bool(side_on is not None and side_on < 0.5),
                              square=bool(side_on is not None and side_on > 0.85)))

    # lunges / low reaches: wide feet and hips low
    lunges = []
    low = (stance > 1.1) & (legh < 0.85 * base_leg) & (rally > 0)
    for g in _group(np.where(low)[0], T, 0.3):
        p = min(g, key=lambda i: legh[i])
        side = "right" if X[p] > 0.3 else ("left" if X[p] < -0.3 else "center")
        lunges.append(dict(t=float(T[p]), rally=int(rally[p]), depth=float(legh[p] / base_leg), lean=float(lean[p]),
                           stance=float(stance[p]), side=side, conf=float(rows[p]["conf"])))

    near_ev = np.zeros(len(T), bool)
    for e in overheads + lunges:
        near_ev |= np.abs(T - e["t"]) < 0.5
    neutral = (rally > 0) & ~near_ev & ~np.isnan(legh)
    rel = legh / base_leg
    high = rel > 0.94

    def share(mask, cond):
        return float(100 * np.mean(cond[mask])) if mask.sum() else None

    rally_secs = float(sum(b - a for a, b in rallies)) or 1.0
    in_r = (rally > 0) & ~np.isnan(X)
    oh = overheads
    m = dict(
        rally_count=len(rallies), rally_minutes=round(rally_secs / 60, 2),
        neutral_high_share=share(neutral, high),
        neutral_narrow_share=share(neutral, stance < shw),
        neutral_leg_rel=float(100 * np.nanmedian(rel[neutral])) if neutral.any() else None,
        oh_count=len(oh),
        oh_turned_share=100 * np.mean([o["turned"] for o in oh]) if oh else None,
        oh_square_share=100 * np.mean([o["square"] for o in oh]) if oh else None,
        oh_leftarm_up_share=100 * np.mean([(o["left_up"] or -1) > 0.2 for o in oh]) if oh else None,
        oh_reach_median=float(np.median([o["reach"] for o in oh])) if oh else None,
        oh_jump_share=100 * np.mean([bool(o["jump"]) for o in oh]) if oh else None,
        lunge_per_min=len(lunges) / (rally_secs / 60),
        lunge_lean_share=100 * np.mean([l["lean"] > 25 for l in lunges]) if lunges else None,
        lunge_left_share=100 * np.mean([l["side"] == "left" for l in lunges]) if lunges else None,
        pos_left_share=share(in_r, X < -0.3), pos_right_share=share(in_r, X > 0.3),
    )
    if break_t is not None:
        m["high_share_after_break"] = share(neutral & (T >= break_t), high)
    per_rally = []
    for k in range(1, len(rallies) + 1):
        mk = neutral & (rally == k)
        if mk.sum() >= 3:
            per_rally.append(dict(rally=k, t=float(rallies[k - 1][0]), high_share=float(100 * np.mean(high[mk]))))
    neutral_frames = [dict(t=float(T[i]), rel=float(rel[i]), stance=float(stance[i]), conf=float(rows[i]["conf"]))
                      for i in np.where(neutral)[0]]
    m = {k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()}
    return m, dict(overheads=overheads, lunges=lunges, per_rally=per_rally, base_leg=base_leg, base_shw=base_shw,
                   neutral_frames=neutral_frames)


def side_metrics(rows, rallies):
    """Metrics from the side camera (45° from the net post). Knee angle and forward trunk lean are visible here."""
    T = np.array([r["t"] for r in rows])
    rally = np.array([label(t, rallies) for t in T])
    knee, stance, legh = _arr(rows, "knee_min"), _arr(rows, "stance"), _arr(rows, "legh")
    lean = _arr(rows, "lean")
    rwa = _arr(rows, "rw_above")
    hi = np.nanpercentile(legh, 75)
    near_ev = np.zeros(len(T), bool)
    for i in np.where(rwa > 0.25)[0]:
        near_ev |= np.abs(T - T[i]) < 0.5
    lunge = (rally > 0) & (stance > 1.1) & (legh < 0.85 * hi)
    for i in np.where(lunge)[0]:
        near_ev |= np.abs(T - T[i]) < 0.5
    neutral = (rally > 0) & ~near_ev & ~np.isnan(knee)
    lunges = []
    for g in _group(np.where(lunge)[0], T, 0.3):
        p = min(g, key=lambda i: knee[i])
        lunges.append(dict(t=float(T[p]), knee=float(knee[p]), trunk=float(lean[p])))
    m = dict(
        side_neutral_knee_median=float(np.nanmedian(knee[neutral])) if neutral.any() else None,
        side_neutral_straight_share=float(100 * np.mean(knee[neutral] > 160)) if neutral.any() else None,
        side_lunge_knee_min_median=float(np.median([l["knee"] for l in lunges])) if lunges else None,
        side_lunge_trunk_fwd_median=float(np.median([l["trunk"] for l in lunges])) if lunges else None,
    )
    m = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}
    return m, dict(lunges=lunges)
