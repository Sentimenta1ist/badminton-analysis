"""Annotated frames (skeleton + angles), a check montage and a rally timeline strip."""
import glob, os
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

EDGES = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (11, 12), (5, 11), (6, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
RIGHT = {6, 8, 10, 12, 14, 16}
FONT_CANDIDATES = ["/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
                   "/Library/Fonts/Arial Unicode.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(size):
    for p in FONT_CANDIDATES + glob.glob("/usr/share/fonts/**/*.ttf", recursive=True):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _ang(a, b, c):
    v1, v2 = a - b, c - b
    return float(np.degrees(np.arccos(np.clip(v1 @ v2 / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9), -1, 1))))


def grab(cap, t, offset=0.0):
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, round((t - offset) * fps)))
    ok, img = cap.read()
    return img if ok else None


def annotate(img, det, label, height=480, show_knees=False):
    """Draw skeleton, knee angles and trunk angle; crop around the player; return PIL image."""
    k = np.array(det[4:]).reshape(17, 3)[:, :2]
    s = max(1, img.shape[0] // 500)
    over = img.copy()
    for a, b in EDGES:
        col = (40, 190, 255) if (a in RIGHT or b in RIGHT) else (255, 170, 50)
        cv2.line(over, tuple(k[a].astype(int)), tuple(k[b].astype(int)), col, 3 * s, cv2.LINE_AA)
    for p in k[5:]:
        cv2.circle(over, tuple(p.astype(int)), 4 * s, (255, 255, 255), -1, cv2.LINE_AA)
    img = cv2.addWeighted(over, 0.85, img, 0.15, 0)
    x0, y0, x1, y1 = det[:4]; h = y1 - y0; cx = (x0 + x1) / 2
    X0, X1 = int(max(0, cx - 0.75 * h)), int(min(img.shape[1], cx + 0.75 * h))
    Y0, Y1 = int(max(0, y0 - 0.35 * h)), int(min(img.shape[0], y1 + 0.2 * h))
    crop = img[Y0:Y1, X0:X1]
    sc = height / crop.shape[0]
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    im = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    dr = ImageDraw.Draw(im)
    f_small, f_big = font(16), font(18)
    for hp, kk, an in (((11, 13, 15), (12, 14, 16)) if show_knees else ()):
        a = _ang(k[hp], k[kk], k[an])
        px = (k[kk] - [X0, Y0]) * sc
        dr.text((px[0] + 8, px[1] - 8), f"{a:.0f}°", font=f_small, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    shm, hipm = (k[5] + k[6]) / 2, (k[11] + k[12]) / 2
    v = shm - hipm
    trunk = np.degrees(np.arctan2(abs(v[0]), -v[1]))
    px = (shm - [X0, Y0]) * sc
    dr.text((px[0] + 10, px[1] - 24), f"корпус {trunk:.0f}° вбок" if not show_knees else f"корпус {trunk:.0f}°", font=f_small, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    dr.rectangle([0, 0, im.width, 30], fill=(0, 0, 0))
    dr.text((8, 5), label, font=f_big, fill=(255, 255, 255))
    return im


def montage(images, cols=4, cell_h=300, out=None):
    ims = [im.resize((int(im.width * cell_h / im.height), cell_h)) for im in images]
    cw = max(im.width for im in ims)
    rows = (len(ims) + cols - 1) // cols
    canvas = Image.new("RGB", (cw * cols, cell_h * rows), (0, 0, 0))
    for i, im in enumerate(ims):
        canvas.paste(im, ((i % cols) * cw, (i // cols) * cell_h))
    if out:
        canvas.save(out, quality=80)
    return canvas


def timeline_strip(video, rallies, out, every=None, offset=0.0, width=160, cols=12, max_cells=144):
    """One image to check rally detection: a frame every N seconds, red border = inside a detected rally."""
    cap = cv2.VideoCapture(video)
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    every = every or max(3.0, dur / max_cells)
    cells, t = [], 0.0
    f = font(14)
    while t < dur:
        img = grab(cap, t, offset)
        if img is None:
            break
        h = int(img.shape[0] * width / img.shape[1])
        im = Image.fromarray(cv2.cvtColor(cv2.resize(img, (width, h)), cv2.COLOR_BGR2RGB))
        dr = ImageDraw.Draw(im)
        inside = any(a <= t <= b for a, b in rallies)
        if inside:
            dr.rectangle([0, 0, width - 1, h - 1], outline=(230, 40, 40), width=4)
        dr.text((5, 3), f"{int(t // 60)}:{int(t % 60):02d}", font=f, fill=(255, 255, 0), stroke_width=2, stroke_fill=(0, 0, 0))
        cells.append(im)
        t += every
    rows = (len(cells) + cols - 1) // cols
    canvas = Image.new("RGB", (width * cols, cells[0].height * rows))
    for i, im in enumerate(cells):
        canvas.paste(im, ((i % cols) * width, (i // cols) * im.height))
    canvas.save(out, quality=70)
    return out
