"""Self-contained HTML: one session report (report.html) and the progress page (progress.html).

Inputs per session folder: notes.json (text written by Claude), metrics.json, events.json, img/*.jpg.
History: metrics.csv (date,session,metric,value,version). Images are embedded as base64, no external files.
"""
import base64, html, io, json, os, re
from .metrics_def import METRICS
from .compare import load_history

KEY = ["neutral_high_share", "neutral_narrow_share", "oh_turned_share", "oh_square_share", "oh_leftarm_up_share",
       "lunge_lean_share", "side_neutral_straight_share", "side_lunge_trunk_fwd_median"]
SHORT = {
    "neutral_high_share": "времени между ударами стоишь высоко",
    "neutral_narrow_share": "того же времени стопы уже плеч",
    "oh_turned_share": "ударов сверху с разворотом",
    "oh_square_share": "ударов сверху грудью к сетке",
    "oh_leftarm_up_share": "ударов сверху с поднятой левой рукой",
    "lunge_lean_share": "выпадов с завалом корпуса >25°",
    "side_neutral_straight_share": "времени колени почти прямые (сбоку)",
    "side_lunge_trunk_fwd_median": "наклон корпуса вперёд в выпаде (сбоку)",
}

CSS = """
:root{--bg:#eef1f6;--surface:#fff;--ink:#152036;--muted:#5a6680;--line:#e2b923;--court:#2b4c8c;--court2:#8aa3d4;
--good:#1f8a5b;--bad:#c2412d;--warn:#b7791f;--grid:#d9dee8;
--display:"Avenir Next Condensed","Roboto Condensed","Arial Narrow",sans-serif;--body:-apple-system,"Segoe UI",system-ui,sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1626;--surface:#18223a;--ink:#e6ebf5;--muted:#9aa6c0;
--line:#f0c83a;--court:#7fa2e6;--court2:#40598f;--good:#4cc08a;--bad:#f07a63;--warn:#e0a84a;--grid:#2a3756;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f1626;--surface:#18223a;--ink:#e6ebf5;--muted:#9aa6c0;--line:#f0c83a;--court:#7fa2e6;--court2:#40598f;
--good:#4cc08a;--bad:#f07a63;--warn:#e0a84a;--grid:#2a3756;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--body);-webkit-text-size-adjust:100%}
main{max-width:980px;margin:0 auto;padding:28px 16px 64px;display:grid;gap:36px}
h1,h2,h3{font-family:var(--display);font-weight:600;line-height:1.15;margin:0;text-wrap:balance}
h1{font-size:clamp(30px,6vw,46px)} h2{font-size:28px;border-left:6px solid var(--line);padding-left:12px} h3{font-size:20px}
p{margin:0;max-width:68ch} a{color:var(--court)}
header{display:grid;gap:10px}
.top{display:flex;justify-content:space-between;align-items:start;gap:12px}
.meta{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--muted);font-size:14px}
.meta b{color:var(--ink);font-weight:600}
.lede{color:var(--muted)}
#theme{font:13px var(--body);background:var(--surface);color:var(--muted);border:1px solid var(--grid);border-radius:99px;padding:4px 12px;cursor:pointer;white-space:nowrap}
section{display:grid;gap:16px;min-width:0}
main>*,section>*,details{min-width:0;max-width:100%}
.card{background:var(--surface);border-radius:10px;padding:18px;display:grid;gap:10px;min-width:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.tile{background:var(--surface);border-radius:10px;padding:14px 16px;border-top:4px solid var(--muted);display:grid;gap:6px;align-content:start}
.tile.good{border-top-color:var(--good)} .tile.bad{border-top-color:var(--bad)}
.tile .n{font-family:var(--display);font-size:38px;font-variant-numeric:tabular-nums;line-height:1}
.tile .l{color:var(--muted);font-size:14px;line-height:1.4}
.d{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums}
.d.good{color:var(--good)} .d.bad{color:var(--bad)} .d.same{color:var(--muted)}
.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
figure{margin:0;background:var(--surface);border-radius:10px;overflow:hidden;display:grid;align-content:start;border-top:4px solid var(--muted)}
figure.good{border-top-color:var(--good)} figure.bad{border-top-color:var(--bad)} figure.warn{border-top-color:var(--warn)}
figure.wide{grid-column:1/-1}
figure img{width:100%;height:auto;display:block;background:#000}
figcaption{padding:10px 12px 12px;font-size:14px;color:var(--muted);line-height:1.45;display:grid;gap:6px}
figcaption b{color:var(--ink)}
.tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin-right:6px}
.tag.good{color:var(--good)} .tag.bad{color:var(--bad)} .tag.warn{color:var(--warn)}
.fix{border-left:4px solid var(--good);padding:2px 0 2px 12px;color:var(--ink)}
.ba{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.ba figure{border-top-width:3px}
.tbl{overflow-x:auto;background:var(--surface);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--grid);white-space:nowrap}
th{font-weight:600;color:var(--muted)}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:99px;white-space:nowrap}
.pill.good{background:color-mix(in srgb,var(--good) 18%,transparent);color:var(--good)}
.pill.bad{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad)}
.pill.same{background:color-mix(in srgb,var(--muted) 18%,transparent);color:var(--muted)}
.chartwrap{background:var(--surface);border-radius:10px;padding:14px;display:grid;gap:6px;min-width:0}
svg.chart{width:100%;height:auto;display:block;overflow:visible}
svg .grid{stroke:var(--grid);stroke-width:1}
svg .ax{fill:var(--muted);font:12px var(--body)}
svg .val{fill:var(--ink);font:600 13px var(--body)}
svg .in{fill:#fff;font:600 13px var(--body)}
@media (max-width:600px){svg.wide .ax{font-size:21px} svg.wide .val,svg.wide .in,svg.wide .goal-l{font-size:22px}}
svg .bar{fill:var(--court)} svg .bar:hover{fill:var(--line)}
svg .brk{stroke:var(--line);stroke-width:2;stroke-dasharray:4 3}
svg .goal-l{fill:var(--good);font:600 12px var(--body);stroke:var(--surface);stroke-width:4px;paint-order:stroke}
svg .goal{stroke:var(--good);stroke-width:1.5;stroke-dasharray:5 4}
svg .ln{fill:none;stroke:var(--court);stroke-width:2.5}
svg .pt{fill:var(--court)}
svg .s-good{fill:var(--good)} svg .s-mid{fill:var(--court2)} svg .s-bad{fill:var(--bad)}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--muted)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.sm{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.sm .chartwrap h3{font:600 14px/1.35 var(--body);color:var(--ink)}
ol,ul{margin:0;padding-left:22px;display:grid;gap:6px;max-width:70ch}
.note{font-size:14px;color:var(--muted)}
details summary{cursor:pointer;color:var(--court);font-weight:600;padding:4px 0}
details[open] summary{margin-bottom:8px}
.ok{color:var(--good);font-weight:600} .no{color:var(--bad);font-weight:600} .na{color:var(--muted)}
.sess{display:grid;gap:12px}
.thumbs{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
.thumbs figure figcaption{font-size:12px;padding:6px 8px 8px}
"""

JS = """<script>
(function(){var r=document.documentElement,b=document.getElementById('theme'),k='bda-theme',m=['auto','light','dark'],
n={auto:'тема: авто',light:'тема: светлая',dark:'тема: тёмная'},s='auto';
try{s=localStorage.getItem(k)||'auto'}catch(e){}
function set(v){s=v;if(v==='auto')r.removeAttribute('data-theme');else r.setAttribute('data-theme',v);b.textContent=n[v];
try{localStorage.setItem(k,v)}catch(e){}}
set(m.indexOf(s)<0?'auto':s);b.onclick=function(){set(m[(m.indexOf(s)+1)%3])};})();
</script>"""


# ---------- helpers
def esc(s):
    return html.escape(str(s), quote=True)


def md(s):
    """Escape, then allow **bold** and `code`."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def tfmt(t):
    t = float(t)
    return f"{int(t // 60)}:{t % 60:04.1f}"


def num(v, k=None):
    if v is None:
        return "—"
    unit = METRICS.get(k, {}).get("unit", "") if k else ""
    if unit == "%":
        return f"{v:.0f}%"
    if unit == "°":
        return f"{v:.0f}°"
    return f"{v:.2f}" if abs(v) < 10 else f"{v:.1f}"


def img_b64(path, max_w=None, q=82):
    if not os.path.exists(path):
        return None
    data = open(path, "rb").read()
    if max_w:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        if im.width > max_w:
            im = im.convert("RGB").resize((max_w, round(im.height * max_w / im.width)))
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=q); data = buf.getvalue()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def page(title, body):
    return (f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{body}</main>{JS}</body></html>')


def history_by_metric(hist):
    out = {}
    for r in hist:
        out.setdefault(r["metric"], []).append((r["date"], float(r["value"]), int(r["version"])))
    for v in out.values():
        v.sort()
    return out


def verdict(k, delta, tol=None):
    d = METRICS[k]
    t = tol if tol is not None else (3.0 if d["unit"] == "%" else 0.05)
    if abs(delta) <= t or d["direction"] == "info":
        return "same"
    return "good" if (delta < 0) == (d["direction"] == "lower") else "bad"


def prev_value(hm, k, date):
    rows = [r for r in hm.get(k, []) if r[0] < date and r[2] == METRICS[k]["version"]]
    return rows[-1] if rows else None


def sessions(root):
    sd = os.path.join(root, "sessions")
    if not os.path.isdir(sd):
        return []
    return sorted(d for d in os.listdir(sd) if os.path.exists(os.path.join(sd, d, "metrics.json")))


def load_json(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default


# ---------- charts (inline SVG)
def chart_rallies(per_rally, break_t=None, goal=None):
    if not per_rally:
        return ""
    W, H, L, R, T, B = 640, 250, 56, 10, 24, 46
    pw, ph = W - L - R, H - T - B
    n = len(per_rally); bw = pw / n
    y = lambda v: T + ph * (1 - v / 100)
    s = [f'<svg viewBox="0 0 {W} {H}" class="chart wide" role="img" aria-label="Доля высокой стойки по розыгрышам">']
    for v in (0, 25, 50, 75, 100):
        s.append(f'<line x1="{L}" x2="{W-R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                 f'<text x="{L-6}" y="{y(v)+4:.1f}" class="ax" text-anchor="end">{v}%</text>')
    brk_x = None
    for i, r in enumerate(per_rally):
        x = L + i * bw; v = r["high_share"]
        s.append(f'<rect class="bar" x="{x+2:.1f}" y="{y(v):.1f}" width="{max(bw-4,1):.1f}" height="{ph-(y(v)-T):.1f}" rx="3">'
                 f'<title>Розыгрыш {r["rally"]} ({tfmt(r["t"])}): {v:.0f}% высоко</title></rect>')
        if n <= 30 and (r["rally"] == 1 or r["rally"] % 5 == 0) or n > 30 and r["rally"] % 10 == 0:
            s.append(f'<text x="{x+bw/2:.1f}" y="{H-B+20}" class="ax" text-anchor="middle">{r["rally"]}</text>')
        if break_t is not None and brk_x is None and r["t"] >= break_t:
            brk_x = x
    if brk_x is not None:
        s.append(f'<line x1="{brk_x:.1f}" x2="{brk_x:.1f}" y1="{T-4}" y2="{H-B}" class="brk"/>'
                 f'<text x="{brk_x+4:.1f}" y="{T+8}" class="ax">перерыв</text>')
    if goal is not None:
        s.append(f'<line x1="{L}" x2="{W-R}" y1="{y(goal):.1f}" y2="{y(goal):.1f}" class="goal"/>'
                 f'<text x="{W-R}" y="{y(goal)-5:.1f}" class="goal-l" text-anchor="end">цель {goal:.0f}%</text>')
    s.append(f'<text x="{L+pw/2:.0f}" y="{H-2}" class="ax" text-anchor="middle">номер розыгрыша</text></svg>')
    return "".join(s)


def chart_trend(points, k, goal=None):
    """Small line chart for one metric over sessions. points: [(date, value)]."""
    W, H, L, R, T, B = 300, 130, 34, 14, 14, 26
    pw, ph = W - L - R, H - T - B
    vals = [v for _, v in points] + ([goal] if goal is not None else [])
    unit = METRICS[k]["unit"]
    lo, hi = (0.0, 100.0) if unit == "%" else (min(vals), max(vals))
    if hi - lo < 1e-6:
        lo, hi = lo - 1, hi + 1
    y = lambda v: T + ph * (1 - (v - lo) / (hi - lo))
    n = len(points)
    x = lambda i: L + (pw / 2 if n == 1 else pw * i / (n - 1))
    s = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="{esc(METRICS[k]["ru"])} по датам">']
    for v in ((0, 50, 100) if unit == "%" else (lo, hi)):
        s.append(f'<line x1="{L}" x2="{W-R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                 f'<text x="{L-5}" y="{y(v)+4:.1f}" class="ax" text-anchor="end">{v:.0f}</text>')
    if goal is not None:
        s.append(f'<line x1="{L}" x2="{W-R}" y1="{y(goal):.1f}" y2="{y(goal):.1f}" class="goal"><title>цель {goal:g}</title></line>')
    if n > 1:
        s.append('<polyline class="ln" points="' + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(points)) + '"/>')
    for i, (d, v) in enumerate(points):
        s.append(f'<circle class="pt" cx="{x(i):.1f}" cy="{y(v):.1f}" r="4"><title>{d}: {num(v, k)}</title></circle>')
        if i == n - 1 or n <= 6:
            s.append(f'<text x="{x(i):.1f}" y="{y(v)-8:.1f}" class="val" text-anchor="middle">{num(v, k)}</text>')
        if n <= 6 or i in (0, n - 1):
            s.append(f'<text x="{x(i):.1f}" y="{H-6}" class="ax" text-anchor="middle">{d[5:]}</text>')
    s.append("</svg>")
    return "".join(s)


def chart_stacked(rows):
    """rows: [(label, [(name, count, cls)])] -> horizontal 100% stacked bars."""
    W, L, R, rh = 640, 140, 10, 38
    H = rh * len(rows) + 6
    pw = W - L - R
    s = [f'<svg viewBox="0 0 {W} {H}" class="chart wide" role="img" aria-label="Распределение">']
    for j, (lab, parts) in enumerate(rows):
        tot = sum(c for _, c, _ in parts) or 1
        y0 = 4 + j * rh; x = L
        s.append(f'<text x="{L-8}" y="{y0+18}" class="ax" text-anchor="end">{esc(lab)}</text>')
        for name, c, cls in parts:
            w = pw * c / tot
            if w <= 0:
                continue
            s.append(f'<rect class="{cls}" x="{x:.1f}" y="{y0}" width="{w:.1f}" height="28" rx="2"><title>{esc(name)}: {c}</title></rect>')
            if w > 28:
                s.append(f'<text x="{x+w/2:.1f}" y="{y0+18}" text-anchor="middle" class="in">{c}</text>')
            x += w
    s.append("</svg>")
    return "".join(s)


def legend(items):
    return '<div class="legend">' + "".join(
        f'<span><i style="background:var(--{c})"></i>{esc(n)}</span>' for n, c in items) + "</div>"


# ---------- blocks
def tile(k, v, prev):
    if prev is None:
        d = '<span class="d same">первая точка</span>'; cls = "same"
    else:
        delta = v - prev[1]; cls = verdict(k, delta)
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "•")
        unit = " п.п." if METRICS[k]["unit"] == "%" else ""
        word = {"good": "лучше", "bad": "хуже", "same": "так же"}[cls]
        d = f'<span class="d {cls}">{arrow} {abs(delta):.1f}{unit} · {word} (к {prev[0]})</span>'
    cls_tile = cls if cls in ("good", "bad") else ""
    return (f'<div class="tile {cls_tile}"><div class="n">{num(v, k)}</div>'
            f'<div class="l">{esc(SHORT.get(k, METRICS[k]["ru"]))}</div>{d}</div>')


def task_target(task):
    return f'{"≤" if task.get("op", "<=") == "<=" else "≥"} {task["target"]:g}'


def task_done(task, v):
    if v is None:
        return None
    return v <= task["target"] if task.get("op", "<=") == "<=" else v >= task["target"]


def figure(f, sd, ba=False):
    src = img_b64(os.path.join(sd, f["file"]))
    if not src:
        return ""
    v = f.get("verdict", "")
    tag = {"good": "хорошо", "bad": "плохо", "warn": "спорно"}.get(v, "")
    wide = " wide" if f.get("wide") else ""
    cap = []
    if not ba:
        head = (f'<span class="tag {v}">{tag}</span>' if tag else "") + (f'<b>{tfmt(f["t"])}.</b> ' if f.get("t") is not None else "")
        cap.append(f'<span>{head}{md(f.get("caption", ""))}</span>')
        if f.get("fix"):
            cap.append(f'<span class="fix">{md(f["fix"])}</span>')
    else:
        cap.append(f'<span>{md(f.get("caption", ""))}</span>')
    return (f'<figure class="{v}{wide}"><img src="{src}" alt="{esc(f.get("caption", ""))[:120]}" loading="lazy">'
            f'<figcaption>{"".join(cap)}</figcaption></figure>')


def frames_block(frames, sd):
    good = [f for f in frames if f.get("verdict") == "good"]
    rest = [f for f in frames if f.get("verdict") != "good"]
    ordered = []
    # pairs: good next to bad
    while good or rest:
        if good:
            ordered.append(good.pop(0))
        if rest:
            ordered.append(rest.pop(0))
    return '<div class="pair">' + "".join(figure(f, sd) for f in ordered) + "</div>"


def oh_table(oh):
    rows = []
    for o in oh:
        sh = ("good", "разворот") if o["turned"] else (("bad", "грудью к сетке") if o["square"] else ("same", "частично"))
        lu = o.get("left_up")
        la = ("same", "нет данных") if lu is None else (("good", "вверху") if lu > 0.2 else (("same", "у плеча") if lu > 0 else ("bad", "внизу")))
        rows.append(f'<tr><td>{tfmt(o["t"])}</td><td>{o["rally"]}</td><td><span class="pill {sh[0]}">{sh[1]}</span></td>'
                    f'<td><span class="pill {la[0]}">{la[1]}</span></td><td>{o["reach"]:.2f}</td><td>{"да" if o.get("jump") else "—"}</td></tr>')
    return ('<div class="tbl"><table><thead><tr><th>Время</th><th>Розыгрыш</th><th>Плечи</th><th>Левая рука</th>'
            '<th>Высота кисти*</th><th>Прыжок</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def lunge_table(lg):
    sides = {"left": "влево", "right": "вправо", "center": "центр"}
    rows = []
    for l in lg:
        lean = f'<span class="pill {"bad" if l["lean"] > 25 else "good"}">{l["lean"]:.0f}°</span>'
        rows.append(f'<tr><td>{tfmt(l["t"])}</td><td>{l["rally"]}</td><td>{sides.get(l["side"], l["side"])}</td>'
                    f'<td>{lean}</td><td>{100*l["depth"]:.0f}%</td><td>{l["stance"]:.2f}</td></tr>')
    return ('<div class="tbl"><table><thead><tr><th>Время</th><th>Розыгрыш</th><th>Сторона</th><th>Корпус вбок</th>'
            '<th>Таз, % от ходьбы</th><th>Ширина стоп**</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


# ---------- report.html
def build_report(sd, history_path=None):
    notes = load_json(os.path.join(sd, "notes.json"), {})
    metrics = load_json(os.path.join(sd, "metrics.json"), {})
    ev = load_json(os.path.join(sd, "events.json"), {})
    back = ev.get("back") or {}
    date = notes.get("date") or os.path.basename(os.path.normpath(sd))
    hm = history_by_metric(load_history(history_path) if history_path else [])
    root = os.path.dirname(os.path.dirname(os.path.normpath(sd)))
    earlier = [d for d in sessions(root) if d < date]
    prev_sd = os.path.join(root, "sessions", earlier[-1]) if earlier else None
    prev_notes = load_json(os.path.join(prev_sd, "notes.json"), {}) if prev_sd else {}
    goals = {t["metric"]: t["target"] for t in notes.get("tasks", [])}
    out = []

    # header
    meta = [("Дата", date), ("Соперник", notes.get("opponent")), ("Счёт", notes.get("score")),
            ("Камеры", notes.get("cameras")), ("Длительность", notes.get("duration")),
            ("Розыгрышей", metrics.get("rally_count")), ("Чистое время", f'{metrics["rally_minutes"]:.1f} мин' if metrics.get("rally_minutes") else None)]
    out.append('<header><div class="top"><h1>' + esc(notes.get("title", f"Разбор {date}")) +
               '</h1><button id="theme" type="button">тема: авто</button></div><div class="meta">' +
               "".join(f"<span>{esc(a)}: <b>{esc(b)}</b></span>" for a, b in meta if b not in (None, "")) + "</div>" +
               (f'<p class="lede">{md(notes["lede"])}</p>' if notes.get("lede") else "") + "</header>")

    # tiles
    tiles = [tile(k, metrics[k], prev_value(hm, k, date)) for k in KEY if metrics.get(k) is not None]
    out.append('<section><h2>Главное в цифрах</h2><div class="tiles">' + "".join(tiles) + "</div>" +
               ("<div class=\"card\"><ol>" + "".join(f"<li>{md(x)}</li>" for x in notes["main"]) + "</ol></div>" if notes.get("main") else "") +
               "</section>")

    # previous tasks
    pt = prev_notes.get("tasks", [])
    if pt:
        rows = []
        for t in pt:
            v = metrics.get(t["metric"]); ok = task_done(t, v)
            st = '<span class="na">нет данных</span>' if ok is None else ('<span class="ok">выполнено</span>' if ok else '<span class="no">нет</span>')
            rows.append(f'<tr><td>{esc(t["what"])}</td><td>{esc(METRICS.get(t["metric"], {}).get("ru", t["metric"]))}</td>'
                        f'<td>{t.get("now", "—")}</td><td>{task_target(t)}</td><td>{num(v, t["metric"]) if v is not None else "—"}</td><td>{st}</td></tr>')
        done = sum(1 for t in pt if task_done(t, metrics.get(t["metric"])))
        out.append(f'<section><h2>Задания прошлого раза: {done} из {len(pt)}</h2><div class="tbl"><table><thead><tr>'
                   '<th>Что</th><th>Метрика</th><th>Было</th><th>Цель</th><th>Факт</th><th>Итог</th></tr></thead><tbody>' +
                   "".join(rows) + f'</tbody></table></div><p class="note">Задания из разбора {esc(earlier[-1])}.</p></section>')
    else:
        out.append('<section><h2>Задания прошлого раза</h2><div class="card"><p>Это первая сессия: заданий прошлого раза нет, '
                   'цифры ниже стали точкой отсчёта.</p></div></section>')

    # charts
    ch = ['<section><h2>Графики</h2>']
    pr = back.get("per_rally", [])
    if pr:
        ch.append('<div class="chartwrap"><h3>Высоко между ударами, по розыгрышам</h3>' +
                  chart_rallies(pr, notes.get("break_t"), goals.get("neutral_high_share")) +
                  '<p class="note">Доля времени между ударами, когда стоишь так же высоко, как при ходьбе. Ниже = лучше. '
                  'Наведи или нажми на столбец, чтобы увидеть время.</p></div>')
    oh = back.get("overheads", [])
    if oh:
        turned = sum(o["turned"] for o in oh); square = sum(o["square"] for o in oh)
        lu = [o.get("left_up") for o in oh]
        up = sum(1 for v in lu if v is not None and v > 0.2); mid = sum(1 for v in lu if v is not None and 0 < v <= 0.2)
        down = len(oh) - up - mid
        ch.append(f'<div class="chartwrap"><h3>Удары сверху: {len(oh)}</h3>' +
                  chart_stacked([("Плечи", [("разворот", turned, "s-good"), ("частично", len(oh) - turned - square, "s-mid"), ("грудью к сетке", square, "s-bad")]),
                                 ("Левая рука", [("вверху", up, "s-good"), ("у плеча", mid, "s-mid"), ("внизу", down, "s-bad")])]) +
                  legend([("разворот / левая вверху", "good"), ("частично / у плеча", "court2"), ("грудью к сетке / левая внизу", "bad")]) + "</div>")
    lg = back.get("lunges", [])
    if lg:
        cnt = {s: [l for l in lg if l["side"] == s] for s in ("left", "center", "right")}
        rows = [(lab, [("ровно", sum(l["lean"] <= 25 for l in cnt[s]), "s-good"), ("завал >25°", sum(l["lean"] > 25 for l in cnt[s]), "s-bad")])
                for lab, s in (("Влево", "left"), ("Центр", "center"), ("Вправо", "right"))]
        mx = max(len(v) for v in cnt.values()) or 1
        # absolute bars (not 100%): scale each row by its count
        W, L, R, rh = 640, 110, 50, 38; pw = W - L - R
        s = [f'<svg viewBox="0 0 {W} {rh*3+6}" class="chart wide" role="img" aria-label="Выпады по сторонам">']
        for j, (lab, parts) in enumerate(rows):
            y0 = 4 + j * rh; x = L
            s.append(f'<text x="{L-8}" y="{y0+18}" class="ax" text-anchor="end">{lab}</text>')
            for name, c, cls in parts:
                w = pw * c / mx
                if w > 0:
                    s.append(f'<rect class="{cls}" x="{x:.1f}" y="{y0}" width="{w:.1f}" height="28" rx="2"><title>{name}: {c}</title></rect>')
                x += w
            s.append(f'<text x="{x+6:.1f}" y="{y0+18}" class="val">{sum(c for _, c, _ in parts)}</text>')
        s.append("</svg>")
        ch.append(f'<div class="chartwrap"><h3>Выпады: {len(lg)}, по сторонам</h3>' + "".join(s) +
                  legend([("корпус ровно", "good"), ("завал корпуса >25°", "bad")]) +
                  '<p class="note">Сторона по положению стоп относительно центра корта (±0.3 м). Зависит от того, ровно ли стоит задняя камера.</p></div>')
    # trend (key metrics, all sessions)
    sm = []
    for k in KEY:
        pts = [(d, v) for d, v, ver in hm.get(k, []) if ver == METRICS[k]["version"]]
        if pts:
            sm.append(f'<div class="chartwrap"><h3>{esc(METRICS[k]["ru"])}</h3>{chart_trend(pts, k, goals.get(k))}</div>')
    if sm:
        ch.append('<h3>Тренд по всем сессиям</h3><div class="sm">' + "".join(sm) + "</div>"
                  '<p class="note">Зелёная пунктирная линия — цель из заданий этой сессии.</p>')
    ch.append("</section>")
    out.append("".join(ch))

    # sections with frames
    for sec in notes.get("sections", []):
        body = [f'<section><h2>{esc(sec["title"])}</h2>']
        if sec.get("text"):
            body.append('<div class="card">' + "".join(f"<p>{md(p)}</p>" for p in sec["text"]) + "</div>")
        if sec.get("frames"):
            body.append(frames_block(sec["frames"], sd))
        if sec.get("fix"):
            body.append(f'<p class="fix">{md(sec["fix"])}</p>')
        body.append("</section>")
        out.append("".join(body))

    # before / after
    if prev_notes:
        cur = {f.get("kind"): f for s in notes.get("sections", []) for f in s.get("frames", []) if f.get("kind")}
        old = {f.get("kind"): f for s in prev_notes.get("sections", []) for f in s.get("frames", []) if f.get("kind")}
        pairs = [(old[k], cur[k]) for k in cur if k in old]
        if pairs:
            blocks = []
            for o, c in pairs:
                o2 = dict(o, caption=f'Было, {earlier[-1]} {tfmt(o["t"]) if o.get("t") is not None else ""}')
                c2 = dict(c, caption=f'Стало, {date} {tfmt(c["t"]) if c.get("t") is not None else ""}')
                blocks.append('<div class="card"><h3>' + esc(c.get("kind_ru") or c.get("kind")) + '</h3><div class="ba">' +
                              figure(o2, prev_sd, True) + figure(c2, sd, True) + "</div></div>")
            out.append('<section><h2>Было / стало</h2>' + "".join(blocks) + "</section>")

    # events tables
    if oh or lg:
        t = ['<section><h2>Все удары сверху и выпады</h2>']
        if oh:
            t.append(f'<details open><summary>Удары сверху ({len(oh)})</summary>{oh_table(oh)}'
                     '<p class="note">* Насколько правая кисть выше головы в верхней точке, в длинах корпуса.</p></details>')
        if lg:
            t.append(f'<details><summary>Выпады ({len(lg)})</summary>{lunge_table(lg)}'
                     '<p class="note">** Расстояние между стопами в длинах корпуса.</p></details>')
        t.append("</section>")
        out.append("".join(t))

    # new tasks
    if notes.get("tasks"):
        rows = "".join(f'<tr><td>{esc(t["what"])}</td><td>{esc(METRICS.get(t["metric"], {}).get("ru", t["metric"]))}</td>'
                       f'<td>{num(metrics.get(t["metric"]), t["metric"])}</td><td><b>{task_target(t)}</b></td></tr>' for t in notes["tasks"])
        drills = ('<div class="card"><h3>Упражнения</h3><ul>' + "".join(f"<li>{md(d)}</li>" for d in notes["drills"]) + "</ul></div>") if notes.get("drills") else ""
        out.append('<section><h2>Задания на следующий разбор</h2><div class="tbl"><table><thead><tr><th>Что</th><th>Метрика</th>'
                   f'<th>Сейчас</th><th>Цель</th></tr></thead><tbody>{rows}</tbody></table></div>{drills}</section>')

    if notes.get("limits"):
        out.append('<section><h2>Ограничения</h2><div class="card"><ul class="note">' +
                   "".join(f"<li>{md(x)}</li>" for x in notes["limits"]) + "</ul></div></section>")
    if notes.get("links"):
        out.append('<section><h2>Ссылки</h2><div class="card"><ul>' +
                   "".join(f'<li><a href="{esc(l["url"])}">{esc(l["title"])}</a></li>' for l in notes["links"]) + "</ul></div></section>")

    path = os.path.join(sd, "report.html")
    open(path, "w").write(page(f"Бадминтон {date}", "".join(out)))
    return path


# ---------- progress.html
def build_progress(root, history_path=None):
    history_path = history_path or os.path.join(root, "metrics.csv")
    hm = history_by_metric(load_history(history_path))
    ss = sessions(root)
    last_notes = load_json(os.path.join(root, "sessions", ss[-1], "notes.json"), {}) if ss else {}
    goals = {t["metric"]: t["target"] for t in last_notes.get("tasks", [])}
    out = [f'<header><div class="top"><h1>Бадминтон: прогресс</h1><button id="theme" type="button">тема: авто</button></div>'
           f'<div class="meta"><span>Сессий: <b>{len(ss)}</b></span>' +
           (f'<span>С <b>{ss[0]}</b> по <b>{ss[-1]}</b></span>' if ss else "") + "</div>"
           '<p class="lede">Все метрики по датам, лучшие кадры каждой сессии и ссылки на полные разборы. '
           'Зелёная пунктирная линия — цель из последних заданий.</p></header>']
    if ss:
        last = load_json(os.path.join(root, "sessions", ss[-1], "metrics.json"), {})
        out.append(f'<section><h2>Последняя сессия, {ss[-1]}</h2><div class="tiles">' +
                   "".join(tile(k, last[k], prev_value(hm, k, ss[-1])) for k in KEY if last.get(k) is not None) + "</div></section>")
    groups = [("Ноги между ударами", lambda k: k.startswith("neutral_") or k == "high_share_after_break"),
              ("Удар сверху", lambda k: k.startswith("oh_")), ("Выпады", lambda k: k.startswith("lunge_")),
              ("Сбоку", lambda k: k.startswith("side_")), ("Позиция и объём", lambda k: True)]
    used = set()
    for title, match in groups:
        ks = [k for k in METRICS if k not in used and match(k) and hm.get(k)]
        if not ks:
            continue
        used.update(ks)
        charts = "".join(
            f'<div class="chartwrap"><h3>{esc(METRICS[k]["ru"])}</h3>'
            f'{chart_trend([(d, v) for d, v, ver in hm[k] if ver == METRICS[k]["version"]], k, goals.get(k))}</div>' for k in ks)
        out.append(f'<section><h2>{esc(title)}</h2><div class="sm">{charts}</div></section>')
    sess = []
    for d in reversed(ss):
        sd = os.path.join(root, "sessions", d)
        n = load_json(os.path.join(sd, "notes.json"), {})
        frames = [f for s in n.get("sections", []) for f in s.get("frames", [])]
        best = [f for f in frames if f.get("best")] or [f for f in frames if f.get("verdict") == "good"][:2] + [f for f in frames if f.get("verdict") == "bad"][:2]
        th = []
        for f in best[:6]:
            src = img_b64(os.path.join(sd, f["file"]), max_w=420, q=72)
            if src:
                v = f.get("verdict", "")
                th.append(f'<figure class="{v}"><img src="{src}" alt="" loading="lazy"><figcaption>'
                          f'<span><b>{tfmt(f["t"]) if f.get("t") is not None else ""}</b> {esc(f.get("short") or f.get("kind_ru") or "")}</span></figcaption></figure>')
        link = f"sessions/{d}/report.html"
        has = os.path.exists(os.path.join(root, link))
        meta = " · ".join(x for x in [n.get("opponent") and f"соперник: {n['opponent']}", n.get("score") and f"счёт {n['score']}", n.get("cameras")] if x)
        sess.append(f'<div class="card"><h3>{"<a href=\"" + link + "\">" if has else ""}{esc(d)}{"</a>" if has else ""}</h3>'
                    f'<p class="note">{esc(meta)}</p>' + (f'<div class="thumbs">{"".join(th)}</div>' if th else "") +
                    (f'<p><a href="{link}">Полный разбор →</a></p>' if has else "") + "</div>")
    out.append('<section><h2>Сессии</h2><div class="sess">' + "".join(sess) + "</div></section>")
    path = os.path.join(root, "progress.html")
    open(path, "w").write(page("Бадминтон: прогресс", "".join(out)))
    return path
