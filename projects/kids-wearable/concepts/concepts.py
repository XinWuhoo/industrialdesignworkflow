"""Generate concept sheets and Vizcom line inputs. Usage: python3 concepts.py <out_dir>; then node render.js <out_dir>."""
import math
import sys

OUT = sys.argv[1]

C = {  # project CMF colours (see projects/kids-wearable/cmf.json)
    "cream": "#F4EFE6", "sky": "#8EC5E8", "berry": "#E86A8E", "sunny": "#F6C945",
    "mint": "#8FD3B6", "screen": "#1E2430", "ink": "#1C1D1F", "muted": "#5D6063",
    "line": "#DCD9D2", "surface": "#F6F5F2", "skin": "#EDE3D8",
}
S = 5  # px per mm, top view
W, H = 1400, 1150


def rr(x, y, w, h, r, cls, extra=""):
    return f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r:.1f}" {extra}/>'


def circ(cx, cy, r, cls):
    return f'<circle class="{cls}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}"/>'


def mm(v):
    return v * S


class View:
    def __init__(self, mode):
        self.mode = mode  # "sheet" or "line"
        self.els = []

    def add(self, s):
        self.els.append(s)


def style(mode):
    if mode == "line":
        return """
      .f, .f2, .f3, .scr, .acc { fill:#fff; stroke:#111; stroke-width:3; }
      .scr { fill:#fff; } .thin { fill:none; stroke:#111; stroke-width:1.5; }
      .hole { fill:#fff; stroke:#111; stroke-width:2; }
      .ui { fill:none; stroke:#111; stroke-width:2; }
      .wrist, .dim, text, .lead, .num, .numt { display:none; }"""
    return f"""
      .f {{ fill:var(--a); stroke:{C['ink']}; stroke-width:2.5; }}
      .f2 {{ fill:var(--b); stroke:{C['ink']}; stroke-width:2.5; }}
      .f3 {{ fill:var(--c); stroke:{C['ink']}; stroke-width:2.5; }}
      .acc {{ fill:var(--d); stroke:{C['ink']}; stroke-width:2.5; }}
      .scr {{ fill:{C['screen']}; stroke:{C['ink']}; stroke-width:2; }}
      .ui {{ fill:none; stroke:{C['cream']}; stroke-width:3; stroke-linecap:round; }}
      .thin {{ fill:none; stroke:{C['ink']}; stroke-width:1.2; }}
      .hole {{ fill:{C['surface']}; stroke:{C['ink']}; stroke-width:1.5; }}
      .wrist {{ fill:{C['skin']}; stroke:{C['muted']}; stroke-width:1.5; stroke-dasharray:6 5; }}
      .dim {{ fill:none; stroke:{C['muted']}; stroke-width:1.2; }}
      .lead {{ fill:none; stroke:{C['muted']}; stroke-width:1.2; }}
      .num {{ fill:#fff; stroke:{C['ink']}; stroke-width:1.5; }}
      .numt {{ font:600 14px Inter, sans-serif; fill:{C['ink']}; text-anchor:middle; dominant-baseline:central; }}
      text {{ font-family:Inter, sans-serif; fill:{C['ink']}; }}
      .h1 {{ font-size:40px; font-weight:600; letter-spacing:-.01em; }}
      .tag {{ font-size:18px; fill:{C['muted']}; }}
      .lab {{ font-size:17px; }}
      .code {{ font:600 13px ui-monospace, Menlo, monospace; fill:{C['muted']}; }}
      .cap {{ font:600 13px Inter, sans-serif; fill:{C['muted']}; letter-spacing:.08em; }}"""


def strap(cx, y0, length, w_start, w_end, direction, cls):
    """Tapered strap from y0 going up (direction=-1) or down (+1); returns path."""
    y1 = y0 + direction * length
    a, b = w_start / 2, w_end / 2
    r = b
    yr = y1 - direction * r
    return (f'<path class="{cls}" d="M{cx - a:.1f} {y0:.1f} L{cx - b:.1f} {yr:.1f} '
            f'A{r:.1f} {r:.1f} 0 0 {1 if direction < 0 else 0} {cx + b:.1f} {yr:.1f} L{cx + a:.1f} {y0:.1f} Z"/>')


def callout(v, n, x, y, tx, ty, text, code=""):
    v.add(f'<path class="lead" d="M{x:.1f} {y:.1f} L{tx - 18:.1f} {ty:.1f}"/>')
    v.add(circ(tx, ty, 13, "num") + f'<text class="numt" x="{tx:.1f}" y="{ty:.1f}">{n}</text>')
    v.add(f'<text class="lab" x="{tx + 22:.1f}" y="{ty + 6:.1f}">{text}</text>')
    if code:
        v.add(f'<text class="code" x="{tx + 22:.1f}" y="{ty + 24:.1f}">{code}</text>')


def side_view(v, cx, cy, kind, pod_w, pod_t):
    """Pod on a child's wrist cross-section (46 x 36 mm), 7 px/mm."""
    k = 7
    rx, ry = 23 * k, 18 * k
    band = 2.8 * k
    v.add(f'<ellipse class="wrist" cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/>')
    if kind == "bead":
        n = 22
        for i in range(n):
            a0 = math.pi * 0.5 + (i / n) * 2 * math.pi
            if abs(math.sin(a0) - (-1)) < 0.12:  # skip under the pod (top)
                continue
            x = cx + (rx + band / 2) * math.cos(a0)
            y = cy + (ry + band / 2) * math.sin(a0)
            ang = math.degrees(math.atan2(ry * math.cos(a0), -rx * math.sin(a0)))
            cls = "f2" if i % 2 else "f3"
            v.add(f'<rect class="{cls}" x="{x - 0.9 * k * 6 / 6 * 6:.1f}" y="{y - band * 0.75:.1f}" width="{10.8 * k / 1.8:.1f}" '
                  f'height="{band * 1.5:.1f}" rx="{band * 0.75:.1f}" transform="rotate({ang:.1f} {x:.1f} {y:.1f})"/>')
    else:
        v.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + band / 2}" ry="{ry + band / 2}" '
              f'style="fill:none;stroke:{C["ink"]};stroke-width:{band + 5}"/>')
        v.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + band / 2}" ry="{ry + band / 2}" '
              f'style="fill:none;stroke:var(--b);stroke-width:{band}"/>')
    top = cy - ry - band * 0.6
    w, t = pod_w * k, pod_t * k
    x0 = cx - w / 2
    # domed pod: flat-ish bottom following the wrist, domed top
    v.add(f'<path class="f" d="M{x0:.1f} {top:.1f} C{x0:.1f} {top - t * 0.85:.1f} {x0 + w * 0.12:.1f} {top - t:.1f} {cx:.1f} {top - t:.1f} '
          f'C{x0 + w * 0.88:.1f} {top - t:.1f} {x0 + w:.1f} {top - t * 0.85:.1f} {x0 + w:.1f} {top:.1f} '
          f'Q{cx:.1f} {top + 0.18 * t:.1f} {x0:.1f} {top:.1f} Z"/>')
    if kind == "bumper":
        v.add(f'<path class="thin" d="M{x0 + 3 * k:.1f} {top - t * 0.25:.1f} H{x0 + w - 3 * k:.1f}"/>')
        v.add(circ(x0 + 2 * k, top - t * 0.95, 4.5 * k / 1.6, "f2"))
        v.add(circ(x0 + w - 2 * k, top - t * 0.95, 4.5 * k / 1.6, "f2"))
    # thickness dimension
    dx = x0 + w + 26
    v.add(f'<path class="dim" d="M{dx} {top} V{top - t} M{dx - 6} {top} H{dx + 6} M{dx - 6} {top - t} H{dx + 6}"/>')
    v.add(f'<text class="code" x="{dx + 10}" y="{top - t / 2 + 5:.1f}">{pod_t:g} mm</text>')
    v.add(f'<text class="cap" x="{cx}" y="{cy + ry + 60}" text-anchor="middle">SIDE — 46 × 36 MM WRIST</text>')


def pebble(v, cx, cy):
    pw, ph = 34, 38
    v.add(strap(cx, cy - mm(ph / 2) + mm(4), mm(84), mm(20), mm(17), -1, "f2"))
    v.add(strap(cx, cy + mm(ph / 2) - mm(4), mm(72), mm(20), mm(17), 1, "f2"))
    for i in range(7):  # adjustment holes, 6 mm pitch
        v.add(circ(cx, cy - mm(ph / 2) - mm(30) - mm(6 * i), mm(1.3), "hole"))
    ystud = cy + mm(ph / 2) + mm(58)
    v.add(circ(cx, ystud, mm(2.2), "acc"))  # pin stud
    v.add(rr(cx - mm(11), cy + mm(ph / 2) + mm(38), mm(22), mm(7), mm(2), "f2"))  # keeper
    v.add(rr(cx - mm(pw / 2), cy - mm(ph / 2), mm(pw), mm(ph), mm(15), "f"))
    v.add(circ(cx, cy, mm(12), "scr"))
    v.add(rr(cx + mm(pw / 2) - mm(1), cy - mm(5), mm(3), mm(10), mm(1.5), "acc"))  # button
    # UI: simple clock face hint
    v.add(f'<path class="ui" d="M{cx} {cy} V{cy - mm(7)} M{cx} {cy} L{cx + mm(5)} {cy + mm(2)}"/>')
    return pw, 12


def bumper(v, cx, cy):
    v.add(strap(cx, cy - mm(18), mm(80), mm(22), mm(20), -1, "f2"))
    v.add(strap(cx, cy + mm(18), mm(62), mm(22), mm(20), 1, "f2"))
    # sliding loop ring at the end of the lower strap
    yr = cy + mm(18) + mm(62) - mm(4)
    v.add(rr(cx - mm(14), yr, mm(28), mm(8), mm(4), "acc"))
    v.add(rr(cx - mm(10), yr + mm(2.2), mm(20), mm(3.6), mm(1.8), "hole"))
    # tail keeper on upper strap
    v.add(rr(cx - mm(12.5), cy - mm(18) - mm(36), mm(25), mm(6), mm(2), "acc"))
    for s in (-1, 1):  # bear ears
        v.add(circ(cx + s * mm(16), cy - mm(19), mm(6.5), "f2"))
    v.add(rr(cx - mm(21), cy - mm(21), mm(42), mm(42), mm(13), "f2"))  # silicone bumper
    v.add(rr(cx - mm(17.5), cy - mm(17.5), mm(35), mm(35), mm(10), "f"))  # snap-in module
    v.add(rr(cx - mm(13), cy - mm(13), mm(26), mm(26), mm(6), "scr"))
    # smiley UI
    v.add(circ(cx - mm(5), cy - mm(3), mm(1.4), "acc"))
    v.add(circ(cx + mm(5), cy - mm(3), mm(1.4), "acc"))
    v.add(f'<path class="ui" d="M{cx - mm(5)} {cy + mm(4)} Q{cx} {cy + mm(8.5)} {cx + mm(5)} {cy + mm(4)}"/>')
    return 42, 13


def bead(v, cx, cy):
    d = 36
    link_l, link_w, gap = 11, 17, 1
    for direction, n in ((-1, 7), (1, 6)):
        for i in range(n):
            yc = cy + direction * (mm(d / 2) + mm(gap) + mm(link_l / 2) + i * mm(link_l + gap))
            cls = "acc" if (direction < 0 and i == 2) else ("f3" if i % 2 else "f2")
            v.add(rr(cx - mm(link_w / 2), yc - mm(link_l / 2), mm(link_w), mm(link_l), mm(5.5), cls))
            v.add(f'<path class="thin" d="M{cx - mm(4)} {yc:.1f} H{cx + mm(4)}"/>')
    # magnetic clasp at both ends
    ytop = cy - (mm(d / 2) + mm(gap) + 7 * mm(link_l + gap)) - mm(4)
    ybot = cy + (mm(d / 2) + mm(gap) + 6 * mm(link_l + gap)) + mm(4)
    v.add(circ(cx, ytop, mm(5), "f"))
    v.add(circ(cx, ybot, mm(5), "f"))
    v.add(circ(cx, cy, mm(d / 2), "f"))
    v.add(circ(cx, cy, mm(13), "scr"))
    v.add(rr(cx + mm(d / 2) - mm(1.5), cy - mm(3), mm(4), mm(6), mm(2), "acc"))  # crown button
    # UI: step ring
    v.add(f'<path class="ui" d="M{cx} {cy - mm(9)} A{mm(9)} {mm(9)} 0 1 1 {cx - mm(8.5)} {cy - mm(3)}"/>')
    return d, 12


TARGETS = {  # per note: target (mm right of centre, px below centre), label y (px below centre)
    "pebble": [(14, 40, 0), (10, -150, -150), (2.2, 385, 385), (1.3, -300, -270)],
    "bumper": [(16, 50, 40), (22, -95, -130), (14, 385, 385), (12.5, -267, -267)],
    "bead": [(15, 30, 20), (8.5, -125, -140), (5, -243, -250), (5, 476, 440)],
}

DIRS = [
    ("A", "Pebble", "A soft river-stone pod on a one-piece silicone strap. Pin-and-tuck sizing a child can do alone.",
     pebble, "pebble", {"a": C["cream"], "b": C["sky"], "c": C["sky"], "d": C["sunny"]},
     [("Pod — PC/ABS, cream, soft-touch", "CMF-01 · PC-ABS · C-CREAM · F-SOFT"),
      ("Strap — LSR silicone, sky, matte", "CMF-02 · LSR · C-SKY · F-MATTE"),
      ("Button + pin — sunny, gloss", "CMF-03 · PC-ABS · C-SUNNY · F-GLOSS"),
      ("7 holes, 6 mm pitch → 110–160 mm", "sealed pod, 5 ATM")]),
    ("B", "Buddy", "A snap-in module in a bear-eared silicone bumper. Swap the bumper, change the character.",
     bumper, "bumper", {"a": C["cream"], "b": C["berry"], "c": C["berry"], "d": C["sunny"]},
     [("Module — PC/ABS, cream, gloss", "CMF-01 · PC-ABS · C-CREAM · F-GLOSS"),
      ("Bumper + ears + strap — LSR, berry", "CMF-02 · LSR · C-BERRY · F-MATTE"),
      ("Slide ring + keeper — sunny", "CMF-03 · TPE · C-SUNNY · F-SATIN"),
      ("Strap slides through the ring, any length", "module sealed, 5 ATM")]),
    ("C", "Beads", "A round face on a string of chunky silicone beads. Add or remove links as the child grows.",
     bead, "bead", {"a": C["mint"], "b": C["cream"], "c": C["mint"], "d": C["sunny"]},
     [("Face — PC/ABS, mint, satin", "CMF-01 · PC-ABS · C-MINT · F-SATIN"),
      ("Links — LSR, cream / mint alternating", "CMF-02 · LSR · C-CREAM + C-MINT · F-MATTE"),
      ("Name bead + crown — sunny", "CMF-03 · LSR · C-SUNNY · F-GLOSS"),
      ("12 mm links, magnetic ball clasp", "sealed face, 5 ATM")]),
]


def build(letter, name, tagline, fn, kind, palette, notes, mode):
    v = View(mode)
    cx, cy = 300, 600
    pod_w, pod_t = fn(v, cx, cy)
    if mode == "sheet":
        # callouts
        side_view(v, 1165, 420, kind, pod_w, pod_t)
        pts = sorted(zip(TARGETS[kind], notes), key=lambda t: t[0][2])
        for n, ((tx, ty, y), note) in enumerate(pts, 1):
            callout(v, n, cx + mm(tx), cy + ty, 640, cy + y, note[0], note[1])
        # scale bar 20 mm
        v.add(f'<path class="dim" d="M60 1110 H{60 + mm(20)} M60 1104 V1116 M{60 + mm(20)} 1104 V1116"/>')
        v.add(f'<text class="code" x="{70 + mm(20)}" y="1115">20 mm · top view 1:1 at 5 px/mm</text>')
        head = (f'<text class="h1" x="560" y="96">{letter} · {name}</text>'
                f'<text class="tag" x="560" y="132">{tagline}</text>'
                f'<text class="cap" x="60" y="60">TOP — FLAT LAY</text>')
        bg = f'<rect width="{W}" height="{H}" fill="{C["surface"]}"/>'
    else:
        head, bg = "", f'<rect width="{W}" height="{H}" fill="#fff"/>'
    vars_ = ";".join(f"--{k}:{val}" for k, val in palette.items())
    w, h = (W, H) if mode == "sheet" else (600, H)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="{vars_}">'
            f'<style>{style(mode)}</style>{bg}{head}{"".join(v.els)}</svg>')


for d in DIRS:
    for mode in ("sheet", "line"):
        path = f"{OUT}/{d[0]}-{d[1].lower()}-{mode}.svg"
        with open(path, "w") as f:
            f.write(build(*d, mode))
        print(path)
