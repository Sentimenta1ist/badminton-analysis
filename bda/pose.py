"""Run a YOLO pose model over a video and save compact keypoints (keypoints.json.gz).

Format: {"meta": {...}, "frames": [{"t": sec, "d": [[x0,y0,x1,y1, kx1,ky1,kc1, ... x17,y17,c17], ...]}]}
Only keypoints are kept, never pixels, so the file is small (~1-3 MB per 30 min) and lets every
metric be recomputed later without the video.
"""
import gzip, json, sys, time
import cv2


def pick_device(dev):
    if dev != "auto":
        return dev
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return 0
    except Exception:
        pass
    return "cpu"


def run(video, out, fps=15.0, model="yolo11l-pose.pt", device="auto", start=0.0, end=None,
        imgsz=960, camera="back", offset=0.0, log_every=500):
    from ultralytics import YOLO
    m = YOLO(model)
    dev = pick_device(device)
    cap = cv2.VideoCapture(video)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w, h = int(cap.get(3)), int(cap.get(4))
    n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, round(src_fps / fps))
    if start:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(start * src_fps))
    n = int(start * src_fps)
    frames, t0, done = [], time.time(), 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        t = n / src_fps
        if end is not None and t > end:
            break
        if n % step == 0:
            ok, f = cap.retrieve()
            if not ok:
                break
            r = m(f, imgsz=imgsz, verbose=False, conf=0.2, device=dev)[0]
            dets = []
            if r.keypoints is not None and len(r.boxes):
                for b, k, kc in zip(r.boxes.xyxy.cpu().numpy(), r.keypoints.xy.cpu().numpy(),
                                    r.keypoints.conf.cpu().numpy()):
                    row = [round(float(v), 1) for v in b]
                    for (x, y), c in zip(k, kc):
                        row += [round(float(x), 1), round(float(y), 1), round(float(c), 2)]
                    dets.append(row)
            frames.append({"t": round(t + offset, 3), "d": dets})
            done += 1
            if done % log_every == 0:
                el = time.time() - t0
                print(f"  {camera}: {t:7.1f}s of {n_total/src_fps:.0f}s  ({done/el:.1f} frames/s)", file=sys.stderr)
        n += 1
    meta = dict(video=str(video).split("/")[-1], camera=camera, src_fps=src_fps, step=step,
                fps=src_fps / step, width=w, height=h, model=model, imgsz=imgsz, offset=offset)
    with gzip.open(out, "wt") as fh:
        json.dump({"meta": meta, "frames": frames}, fh, separators=(",", ":"))
    return meta


def load(path):
    with gzip.open(path, "rt") as fh:
        return json.load(fh)
