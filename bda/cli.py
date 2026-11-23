"""badminton-analysis CLI.

  python -m bda run --back BACK.mp4 [--side SIDE.mp4] --out WORK --date 2026-11-29 [--history metrics.csv]
  python -m bda recompute --out WORK [--history metrics.csv]       # metrics again from saved keypoints
  python -m bda frames --out WORK --video BACK.mp4 --times "84.5:высоко;220.8:разворот" [--camera back]
  python -m bda report --session SESSION_DIR [--history metrics.csv]   # notes.json + data -> report.html
  python -m bda progress --root BRAIN/badminton                         # all sessions -> progress.html
"""
import argparse, json, os, gzip
import numpy as np
from . import pose, features, rallies as R, events, compare, overlay


def _save(obj, path):
    with open(path, "w") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=float)


def _fmt(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def select_candidates(ev_back, ev_side=None):
    c = []
    oh = ev_back["overheads"]
    good = sorted([o for o in oh if o["turned"] and (o["left_up"] or -1) > 0.2], key=lambda o: -o["reach"])[:2]
    bad = sorted([o for o in oh if o["square"]], key=lambda o: ((o["left_up"] or 0), -(o["side_on"] or 0)))[:3]
    c += [("back", o["t"], "удар: разворот, левая вверху", "oh_good") for o in good]
    c += [("back", o["t"], "удар: грудью к сетке", "oh_bad") for o in bad]
    nf = ev_back["neutral_frames"]
    # typical (not extreme) examples: extremes are usually detection errors
    tall = sorted([n for n in nf if n["stance"] < 0.5 and 0.98 < n["rel"] < 1.06 and n["conf"] > 0.7], key=lambda n: -n["conf"])
    low = sorted([n for n in nf if n["stance"] > 0.8 and 0.72 < n["rel"] < 0.85 and n["conf"] > 0.7], key=lambda n: -n["conf"])
    def spread(lst, k):
        out = []
        for n in lst:
            if all(abs(n["t"] - o["t"]) > 20 for o in out):
                out.append(n)
            if len(out) == k:
                break
        return out
    c += [("back", n["t"], "между ударами: высоко", "tall") for n in spread(tall[:200], 2)]
    c += [("back", n["t"], "между ударами: низкая готовность", "low") for n in spread(low[:200], 2)]
    lg = ev_back["lunges"]
    c += [("back", l["t"], f"выпад: корпус {l['lean']:.0f}°", "lunge_good") for l in sorted([l for l in lg if l["lean"] < 12], key=lambda l: l["depth"])[:1]]
    c += [("back", l["t"], f"выпад: корпус {l['lean']:.0f}°", "lunge_bad") for l in sorted([l for l in lg if l["conf"] > 0.65], key=lambda l: -l["lean"])[:2]]
    if ev_side:
        sl = ev_side["lunges"]
        c += [("side", l["t"], f"сбоку: выпад, колено {l['knee']:.0f}°", "side_lunge") for l in sorted(sl, key=lambda l: l["knee"])[:1]]
        c += [("side", l["t"], f"сбоку: корпус вперёд {l['trunk']:.0f}°", "side_trunk") for l in sorted(sl, key=lambda l: -l["trunk"])[:1]]
    return [dict(id=i + 1, camera=cam, t=float(t), label=lab, kind=k) for i, (cam, t, lab, k) in enumerate(c)]


def render(out, video, kp, cands, offset=0.0, prefix="cand"):
    import cv2
    os.makedirs(f"{out}/frames", exist_ok=True)
    frames = kp["frames"]; ts = np.array([f["t"] for f in frames])
    picks = features.pick_player(frames)
    cap = cv2.VideoCapture(video)
    ims = []
    for c in cands:
        i = int(np.argmin(np.abs(ts - c["t"])))
        if picks[i] is None:
            continue
        img = overlay.grab(cap, frames[i]["t"], offset)
        if img is None:
            continue
        im = overlay.annotate(img, picks[i], f"#{c['id']} {_fmt(frames[i]['t'])}  {c['label']}",
                              show_knees=(c.get("camera") == "side"))
        path = f"{out}/frames/{prefix}_{c['id']:02d}.jpg"
        im.save(path, quality=85); c["file"] = path
        ims.append(im)
    return ims


def analyse(out, kp_back, kp_side, date, history, break_t, rallies_override=None):
    rows_b = features.build_rows(kp_back, "back")
    rpath = f"{out}/rallies.json"
    if rallies_override is not None:
        rl = rallies_override
    elif os.path.exists(rpath):
        rl = json.load(open(rpath))
    else:
        rl = R.detect(rows_b); _save(rl, rpath)
    mb, evb = events.back_metrics(rows_b, rl, break_t)
    ms, evs = {}, None
    if kp_side is not None:
        rows_s = features.build_rows(kp_side, "side")
        ms, evs = events.side_metrics(rows_s, rl)
    metrics = {**mb, **ms}
    _save(metrics, f"{out}/metrics.json")
    evb_slim = {k: v for k, v in evb.items() if k != "neutral_frames"}
    _save(dict(back=evb_slim, side=evs, rallies=rl), f"{out}/events.json")
    hist = compare.load_history(history) if history else []
    md = compare.table(hist, date, metrics)
    open(f"{out}/compare.md", "w").write(md + "\n")
    return metrics, evb, evs, rl


def main():
    ap = argparse.ArgumentParser(prog="bda")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--back", required=True); r.add_argument("--side")
    r.add_argument("--out", required=True); r.add_argument("--date", required=True)
    r.add_argument("--history"); r.add_argument("--break-t", type=float)
    r.add_argument("--start", type=float, default=0.0); r.add_argument("--end", type=float)
    r.add_argument("--fps", type=float, default=15.0); r.add_argument("--model", default="yolo11l-pose.pt")
    r.add_argument("--imgsz", type=int, default=960); r.add_argument("--device", default="auto")
    r.add_argument("--side-offset", type=float, help="seconds to add to side time; default: audio sync")
    rc = sub.add_parser("recompute")
    rc.add_argument("--out", required=True); rc.add_argument("--date", required=True)
    rc.add_argument("--history"); rc.add_argument("--break-t", type=float)
    fr = sub.add_parser("frames")
    fr.add_argument("--out", required=True); fr.add_argument("--video", required=True)
    fr.add_argument("--camera", default="back"); fr.add_argument("--times", required=True)
    fr.add_argument("--offset", type=float, default=0.0)
    rp = sub.add_parser("report")
    rp.add_argument("--session", required=True); rp.add_argument("--history")
    pg = sub.add_parser("progress")
    pg.add_argument("--root", required=True); pg.add_argument("--history")
    a = ap.parse_args()
    if a.cmd in ("report", "progress"):
        from . import report
        root = os.path.expanduser(a.root) if a.cmd == "progress" else None
        hist = os.path.expanduser(a.history) if a.history else None
        print(report.build_report(os.path.expanduser(a.session), hist) if a.cmd == "report" else report.build_progress(root, hist))
        return
    os.makedirs(a.out, exist_ok=True)

    if a.cmd == "run":
        off = 0.0
        if a.side:
            if a.side_offset is None:
                from . import sync
                off = sync.offset(a.back, a.side)
                print(f"side offset (audio): {off:+.2f}s")
            else:
                off = a.side_offset
        for cam, vid, o in (("back", a.back, 0.0), ("side", a.side, off)):
            if not vid:
                continue
            path = f"{a.out}/keypoints_{cam}.json.gz"
            if os.path.exists(path):
                print(f"{cam}: keypoints exist, skipping pose"); continue
            s = max(0.0, a.start - o); e = None if a.end is None else a.end - o
            print(f"{cam}: pose estimation…")
            pose.run(vid, path, a.fps, a.model, a.device, s, e, a.imgsz, cam, o)
        kb = pose.load(f"{a.out}/keypoints_back.json.gz")
        ks = pose.load(f"{a.out}/keypoints_side.json.gz") if a.side else None
        metrics, evb, evs, rl = analyse(a.out, kb, ks, a.date, a.history, a.break_t)
        overlay.timeline_strip(a.back, rl, f"{a.out}/check_timeline.jpg")
        cands = select_candidates(evb, evs)
        ims = render(a.out, a.back, kb, [c for c in cands if c["camera"] == "back"])
        if a.side and ks:
            ims += render(a.out, a.side, ks, [c for c in cands if c["camera"] == "side"], off)
        overlay.montage(ims, out=f"{a.out}/check_frames.jpg")
        _save(cands, f"{a.out}/candidates.json")
        _save(dict(side_offset=off, date=a.date, back=a.back, side=a.side), f"{a.out}/run.json")
        print(json.dumps(metrics, ensure_ascii=False, indent=1))
    elif a.cmd == "recompute":
        kb = pose.load(f"{a.out}/keypoints_back.json.gz")
        ks = pose.load(f"{a.out}/keypoints_side.json.gz") if os.path.exists(f"{a.out}/keypoints_side.json.gz") else None
        metrics, *_ = analyse(a.out, kb, ks, a.date, a.history, a.break_t)
        print(json.dumps(metrics, ensure_ascii=False, indent=1))
    elif a.cmd == "frames":
        kp = pose.load(f"{a.out}/keypoints_{a.camera}.json.gz")
        cands = []
        for i, item in enumerate(a.times.split(";")):
            t, lab = item.split(":", 1)
            cands.append(dict(id=i + 1, camera=a.camera, t=float(t), label=lab))
        render(a.out, a.video, kp, cands, a.offset, prefix=f"pick_{a.camera}")
        for c in cands:
            print(c.get("file"))


if __name__ == "__main__":
    main()
