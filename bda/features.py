"""Per-frame body features of the analysed player (the one nearest to the camera).

COCO keypoints: 0 nose, 5/6 shoulders L/R, 7/8 elbows, 9/10 wrists, 11/12 hips, 13/14 knees, 15/16 ankles.
All lengths are normalised by torso length (shoulder-mid to hip-mid) so they do not depend on how far
the player is from the camera.
"""
import numpy as np

TORSO_M = 0.55  # rough real torso length, only used to print lateral position in metres


def _ang(a, b, c):
    v1, v2 = a - b, c - b
    cs = v1 @ v2 / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
    return float(np.degrees(np.arccos(np.clip(cs, -1, 1))))


def _split(det):
    box = np.array(det[:4])
    k = np.array(det[4:]).reshape(17, 3)
    return box, k[:, :2], k[:, 2]


def pick_player(frames, min_h=80):
    """Tallest person, kept continuous: prefer the detection closest to the previous pick."""
    prev = None
    out = []
    for fr in frames:
        cands = [d for d in fr["d"] if d[3] - d[1] >= min_h]
        if not cands:
            out.append(None); continue
        if prev is None:
            best = max(cands, key=lambda d: d[3] - d[1])
        else:
            pc = np.array([(prev[0] + prev[2]) / 2, prev[3]])
            ph = prev[3] - prev[1]
            def cost(d):
                c = np.array([(d[0] + d[2]) / 2, d[3]])
                h = d[3] - d[1]
                return np.linalg.norm(c - pc) / ph + abs(h - ph) / ph - 0.3 * h / ph
            best = min(cands, key=cost)
            tallest = max(cands, key=lambda d: d[3] - d[1])
            if (tallest[3] - tallest[1]) > 1.6 * (best[3] - best[1]):
                best = tallest
        prev = best
        out.append(best)
    return out


def frame_features(det, camera="back", xc=None, width=None):
    box, k, c = _split(det)
    if c[[11, 12, 13, 14, 15, 16]].min() < 0.3:
        return None
    L = dict(nose=k[0], ls=k[5], rs=k[6], le=k[7], re=k[8], lw=k[9], rw=k[10],
             lh=k[11], rh=k[12], lk=k[13], rk=k[14], la=k[15], ra=k[16])
    hipm, shm = (L["lh"] + L["rh"]) / 2, (L["ls"] + L["rs"]) / 2
    torso = float(np.linalg.norm(shm - hipm)) + 1e-6
    footy = max(L["la"][1], L["ra"][1]); footx = (L["la"][0] + L["ra"][0]) / 2
    r = dict(h=float(box[3] - box[1]), torso=torso, foot_y=float(footy), foot_x=float(footx), conf=float(c[5:].mean()))
    r["kneeL"] = _ang(L["lh"], L["lk"], L["la"]); r["kneeR"] = _ang(L["rh"], L["rk"], L["ra"])
    r["knee_min"] = min(r["kneeL"], r["kneeR"])
    r["legh"] = float((footy - hipm[1]) / torso)
    r["stance"] = float(abs(L["la"][0] - L["ra"][0]) / torso)
    r["shw"] = float(np.linalg.norm(L["ls"] - L["rs"]) / torso)
    v = shm - hipm
    r["lean"] = float(np.degrees(np.arctan2(abs(v[0]), -v[1])))        # trunk from vertical in image plane
    # wrist height above the head; head ~0.45 torso above the shoulders (the nose is hidden from behind)
    r["rw_above"] = float((shm[1] - L["rw"][1]) / torso - 0.45) if c[10] > .3 else None
    r["lw_above"] = float((L["ls"][1] - L["lw"][1]) / torso) if c[9] > .3 else None
    r["elbowR"] = _ang(L["rs"], L["re"], L["rw"]) if c[[6, 8, 10]].min() > .3 else None
    r["ankle_gap_y"] = float(abs(L["la"][1] - L["ra"][1]) / torso)
    if xc is None:
        xc = (width or 0) / 2
    r["X"] = float((footx - xc) / torso * TORSO_M)                       # lateral metres, + = player's right (back cam)
    return r


def build_rows(kp, camera="back", xc=None):
    frames = kp["frames"]
    width = kp["meta"].get("width")
    picks = pick_player(frames)
    rows = []
    for fr, det in zip(frames, picks):
        if det is None:
            continue
        f = frame_features(det, camera, xc, width)
        if f is None:
            continue
        f["t"] = fr["t"]
        rows.append(f)
    return rows
