#!/usr/bin/env python3
"""
tulip-gabs: un ramo de tulipanes hecho solo con caracteres de texto.

Escrito desde cero con pygame-ce. El mismo archivo corre en escritorio
(python main.py) y en el navegador gracias a pygbag (WebAssembly).

Teclas:  Espacio pausa · R reinicia · S captura (escritorio) · Esc salir
Clic / toque: suelta corazones y una ráfaga de viento.
"""

import asyncio
import math
import os
import random
import sys

import pygame

WEB = sys.platform == "emscripten"

# --------------------------------------------------------------- ajustes
MESSAGE = "para ti ♥"          # se puede cambiar con ?msg=... en la web
W, H = 720, 1088                    # lienzo virtual (vertical, para celular)
CW, CH = 9, 16                      # tamaño de cada celda de texto
COLS, ROWS = W // CW, H // CH       # 80 x 68 celdas
FONT_FILE = os.path.join("font", "DejaVuSansMono-Bold.ttf")
FONT_SIZE = 15
FPS = 60

TIP = (360, 950)                    # punta del cono de papel
SWAY_TOP = 200                      # altura donde el balanceo es máximo

SCHEMES = {                         # (color de la base, color de la punta)
    "rojo": ((176, 16, 40), (255, 96, 86)),
    "rosa": ((220, 60, 132), (255, 198, 224)),
    "amarillo": ((232, 156, 16), (255, 244, 132)),
    "morado": ((110, 44, 170), (208, 154, 255)),
    "blanco": ((200, 190, 222), (255, 255, 255)),
    "naranja": ((234, 82, 18), (255, 188, 84)),
    "coral": ((248, 100, 98), (255, 224, 180)),
}

# x, y del centro de la flor, escala, color, capa (z)
TULIPS = [
    (250, 292, 0.92, "morado", 3),
    (360, 240, 0.95, "rosa", 3),
    (470, 292, 0.92, "amarillo", 3),
    (176, 402, 0.95, "rojo", 4),
    (298, 362, 1.00, "blanco", 4),
    (422, 362, 1.00, "naranja", 4),
    (544, 402, 0.95, "rosa", 4),
    (238, 488, 1.00, "amarillo", 5),
    (360, 462, 1.05, "rojo", 5),
    (482, 488, 1.00, "morado", 5),
    (360, 562, 0.95, "coral", 7),
]
BLOOM_ORDER = [8, 1, 4, 10, 6, 2, 9, 3, 0, 5, 7]   # orden en que se abren

# hojas: base, punto de control, punta, ancho máximo
LEAVES = [
    ((346, 780), (262, 640), (140, 566), 22),
    ((372, 780), (470, 640), (590, 560), 22),
    ((350, 780), (300, 600), (226, 440), 16),
    ((368, 780), (428, 600), (500, 432), 16),
    ((340, 790), (226, 560), (112, 318), 17),
    ((380, 790), (494, 560), (606, 322), 17),
]

GREEN_BUD = (96, 168, 84)
STEM = (70, 150, 74)
LEAF = (58, 136, 72)
LEAF_LIGHT = (104, 190, 104)
TISSUE = (238, 176, 200)
KRAFT = (190, 132, 80)
JUTE = (226, 190, 128)
CREAM = (255, 240, 214)
MSG_COLOR = (255, 178, 206)

# ---------------------------------------------------------- línea de tiempo
T_TISSUE = (0.4, 1.6)
T_KRAFT = (1.3, 1.5)
T_TWINE = (2.6, 0.9)
T_STEMS, STEM_GAP, STEM_DUR = 3.3, 0.16, 1.5
T_LEAVES, LEAF_GAP, LEAF_DUR = 4.2, 0.22, 1.8
T_COLOR, COLOR_GAP, COLOR_DUR = 7.6, 0.20, 1.3
T_BLOOM, BLOOM_GAP, BLOOM_DUR = 10.0, 0.42, 1.1
T_MSG = T_BLOOM + BLOOM_GAP * (len(TULIPS) - 1) + BLOOM_DUR + 0.5
MSG_RATE = 0.085


# ------------------------------------------------------------- utilidades
def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (c1[0] + (c2[0] - c1[0]) * t,
            c1[1] + (c2[1] - c1[1]) * t,
            c1[2] + (c2[2] - c1[2]) * t)


def shade(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_back(t, s=1.5):
    t = clamp(t) - 1.0
    return 1 + t * t * ((s + 1) * t + s)


def window(t, start, dur):
    return clamp((t - start) / dur)


def h01(a, b, s=0):
    """Ruido determinista 0..1 para una celda."""
    n = (a * 374761393 + b * 668265263 + s * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def cx(c):
    return c * CW + CW * 0.5


def cy(r):
    return r * CH + CH * 0.5


def key_of(c, r):
    if 0 <= c < COLS and 0 <= r < ROWS:
        return r * COLS + c
    return None


def dir_char(dx, dy):
    """Carácter que sigue la dirección de una línea (en pixeles)."""
    a = math.degrees(math.atan2(-dy, dx)) % 180.0
    if a < 22 or a >= 158:
        return "-"
    if a < 68:
        return "/"
    if a < 112:
        return "|"
    return "\\"


def edge_char(L, R, U, D, sides="()", top="-", bottom="_"):
    if U and L and R:
        return "^"
    if D and L and R:
        return "v"
    if L and R:
        return "|"
    if U and L:
        return "/"
    if U and R:
        return "\\"
    if D and L:
        return "\\"
    if D and R:
        return "/"
    if L:
        return sides[0]
    if R:
        return sides[1]
    if U:
        return top
    if D:
        return bottom
    return None


def bezier(p0, p1, p2, n):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        pts.append((a * p0[0] + b * p1[0] + c * p2[0],
                    a * p0[1] + b * p1[1] + c * p2[1]))
    return pts


def point_in_poly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            if x < xi + (y - yi) * (xj - xi) / (yj - yi):
                inside = not inside
        j = i
    return inside


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = clamp(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy))
    qx, qy = ax + vx * t, ay + vy * t
    return math.hypot(px - qx, py - qy)


def poly_mask(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    mask = set()
    for r in range(int(min(ys) // CH), int(max(ys) // CH) + 1):
        for c in range(int(min(xs) // CW), int(max(xs) // CW) + 1):
            if point_in_poly(cx(c), cy(r), poly):
                mask.add((c, r))
    return mask


def row_spans(mask):
    spans = {}
    for c, r in mask:
        lo, hi = spans.get(r, (c, c))
        spans[r] = (min(lo, c), max(hi, c))
    return spans


# ------------------------------------------------------------ papel y lazo
def build_tissue():
    """Papel de seda rosado que asoma como abanico detrás de las flores."""
    cxp, cyp, rx, ry = 360, 590, 250, 300
    top = []
    for i in range(0, 25):
        a = math.radians(200 + i * 140 / 24)
        k = 1 + 0.035 * math.sin(i * 2.3) + 0.02 * math.sin(i * 5.1)
        top.append((cxp + rx * k * math.cos(a), cyp + ry * k * math.sin(a)))
    poly = [(255, 700), (172, 630)] + top + [(548, 630), (465, 700), (360, 780)]
    mask = poly_mask(poly)
    spans = row_spans(mask)
    cells = []
    for (c, r) in mask:
        y = cy(r)
        L, R = (c - 1, r) not in mask, (c + 1, r) not in mask
        U, D = (c, r - 1) not in mask, (c, r + 1) not in mask
        lo, hi = spans[r]
        xn = (c - lo) / max(1, hi - lo)
        n = h01(c, r, 3)
        e = edge_char(L, R, U, D, sides="()", top="~", bottom="_")
        if e:
            ch, k = e, 0.62
        elif n < 0.5:
            continue
        else:
            ch = "." if n < 0.78 else ":" if n < 0.94 else "'"
            k = 0.20 + 0.14 * math.sin(math.pi * xn) + 0.06 * n
        kk = key_of(c, r)
        if kk is not None:
            cells.append((kk, y, ch, shade(TISSUE, k)))
    return cells


def build_kraft():
    """Papel kraft que envuelve el ramo en forma de cono."""
    top = [(196, 628), (240, 620), (288, 624), (336, 612),
           (384, 606), (432, 604), (478, 596), (524, 594)]
    poly = top + [TIP]
    mask = poly_mask(poly)
    spans = row_spans(mask)
    creases = [(TIP, (300, 622)), (TIP, (440, 603)), ((330, 860), (262, 626))]
    cells = []
    for (c, r) in mask:
        x, y = cx(c), cy(r)
        L, R = (c - 1, r) not in mask, (c + 1, r) not in mask
        U, D = (c, r - 1) not in mask, (c, r + 1) not in mask
        lo, hi = spans[r]
        xn = (c - lo) / max(1, hi - lo)
        n = h01(c, r, 11)
        e = edge_char(L, R, U, D, sides="\\/", top="~", bottom="_")
        lip = (c, r - 2) not in mask
        if e:
            ch, k = e, 0.95
        else:
            ch = None
            for (ax, ay), (bx, by) in creases:
                if seg_dist(x, y, ax, ay, bx, by) < 5.0:
                    ch, k = dir_char(bx - ax, by - ay), 0.42
                    break
            if ch is None:
                ch = ":" if n < 0.42 else ";" if n < 0.70 else "=" if n < 0.86 else "."
                k = 0.36 + 0.34 * math.sin(math.pi * (0.1 + 0.8 * xn)) ** 0.8 + 0.1 * n
                if lip:
                    ch, k = "=", 0.82
        kk = key_of(c, r)
        if kk is not None:
            cells.append((kk, x, ch, shade(KRAFT, k)))
    return cells


def twine_y(x):
    xn = (x - 357) / 73.0
    return 800 + 9 * (1 - xn * xn)


BOW = [
    " .-.   .-. ",
    "(   >@<   )",
    " `-'   `-' ",
]
TAG = [".-'-.", "| ♥ |", "'---'"]


def build_twine():
    band = []
    for c in range(int(284 // CW), int(430 // CW) + 1):
        x = cx(c)
        r = int(twine_y(x) // CH)
        xn = abs(x - 357) / 73.0
        ch = "/" if c % 2 == 0 else "\\"
        band.append((key_of(c, r), x, ch, shade(JUTE, 0.62 + 0.38 * (1 - xn))))
    kc, kr = int(357 // CW), int(twine_y(357) // CH)
    bow = []
    for j, line in enumerate(BOW):
        for i, ch in enumerate(line):
            if ch != " ":
                bow.append((key_of(kc - len(line) // 2 + i, kr - 1 + j), ch))
    tails = [(-1, 2, "/"), (-2, 3, "/"), (-2, 4, "|"), (-3, 5, "/"),
             (1, 2, "\\"), (2, 3, "\\"), (3, 4, "\\")]
    for dc, dr, ch in tails:
        bow.append((key_of(kc + dc, kr + dr), ch))
    for j, line in enumerate(TAG):
        for i, ch in enumerate(line):
            bow.append((key_of(kc + 1 + i, kr + 5 + j), ch))
    return band, bow, (kc, kr)


# ------------------------------------------------------------------ flores
def petal_region(u, v, o):
    """0 = fuera, 1 = pétalos del frente, 2 = pétalos de atrás (entre puntas)."""
    if v > 1.0 or v < -1.0:
        return 0, 0.0
    if v >= 0.12:
        q = (v - 0.12) / 0.88
        hw = math.sqrt(max(0.0, 1.0 - q * q))
    else:
        t = (0.12 - v) / 1.12
        bud = (1.0 - t ** 1.7) ** 0.75
        hw = bud + (1.0 + 0.12 * t - bud) * o
    hw *= 0.7 + 0.3 * min(o, 1.0)
    au = abs(u)
    if au > hw:
        return 0, hw
    if o > 0.02:
        d = 0.46 * o * max(0.0, 1.0 - ((au - 0.48) / 0.28) ** 2)
        if v < -1.0 + d:
            if v < -1.0 + d * 0.5:
                return 0, hw
            return 2, hw
    return 1, hw


PETAL_RAMP = ":=+*#%@"
HEAD_A, HEAD_B = 48, 60            # semiancho y semialto de una flor abierta


def tulip_cells(tp, sp, cp, op, gp):
    x0, y0, scale, scheme, _z = tp
    if sp <= 0:
        return []
    base, tipc = SCHEMES[scheme]
    S = scale * (lerp(0.42, 0.84, ease_out(sp)) + 0.16 * min(op, 1.1))
    A, B = HEAD_A * S, HEAD_B * S
    hx, hy = x0, y0 + (1 - ease_out(sp)) * 26
    c0, c1 = int((hx - A * 1.3) // CW) - 1, int((hx + A * 1.3) // CW) + 1
    r0, r1 = int((hy - B * 1.1) // CH) - 1, int((hy + B * 1.05) // CH) + 1
    reg, info = {}, {}
    top, bot = {}, {}
    for r in range(r0, r1 + 1):
        v = (cy(r) - hy) / B
        for c in range(c0, c1 + 1):
            u = (cx(c) - hx) / A
            g, hw = petal_region(u, v, op)
            reg[(c, r)] = g
            info[(c, r)] = (u, v, hw)
            if g == 1:
                top[c] = min(top.get(c, 99999), r)
                bot[c] = max(bot.get(c, -99999), r)
    cells = []
    seam_tol = 0.55 * CW / A
    for (c, r), g in reg.items():
        if g == 0:
            continue
        kk = key_of(c, r)
        if kk is None:
            continue
        u, v, hw = info[(c, r)]
        au = abs(u)
        n = h01(c, r, 7)
        petal = mix(base, tipc, smooth((1 - v) / 2) ** 1.1)
        m = smooth((cp * 1.35 - (v + 1) / 2) / 0.3)
        col = mix(mix(GREEN_BUD, (150, 210, 120), (1 - v) / 2 * 0.5), petal, m)
        if g == 2:
            # pétalos de atrás, visibles entre las puntas
            b = 0.30 + 0.12 * n
            col = mix(col, base, 0.5 * m)
            ch = "." if n < 0.5 else ":"
        else:
            su = 0.5 * hw * ((1 - v) / 2) ** 0.65
            front = au < su
            cyl = 1 - 0.38 * (au / max(hw, 0.05)) ** 2
            b = (0.95 if front or op < 0.3 else 0.72) * cyl * (0.82 + 0.18 * (1 - v) / 2)
            b += (n - 0.5) * 0.14
            ch = None
            if top.get(c) == r:
                tl, tr = top.get(c - 1, 99999), top.get(c + 1, 99999)
                if tl > r and tr > r:
                    ch = "^"
                elif tl < r and tr < r:
                    ch = "v"
                elif tl > r or tr < r:
                    ch = "/"
                elif tr > r or tl < r:
                    ch = "\\"
                else:
                    ch = "-"
            elif bot.get(c) == r:
                bl, br = bot.get(c - 1, -99999), bot.get(c + 1, -99999)
                if bl < r and br < r:
                    ch = "v"
                elif bl < r:
                    ch = "\\"
                elif br < r:
                    ch = "/"
                else:
                    ch = "_"
            elif reg.get((c - 1, r), 0) != 1:
                ch = "("
            elif reg.get((c + 1, r), 0) != 1:
                ch = ")"
            if ch is not None:
                b += 0.14
            elif op > 0.35 and abs(au - su) < seam_tol and -0.8 < v < 0.8:
                ch = ("\\" if u < 0 else "/") if v < 0.3 else ("(" if u < 0 else ")")
                b *= 0.74
            else:
                ch = PETAL_RAMP[int(clamp(b) * (len(PETAL_RAMP) - 0.01))]
        b = clamp(b + gp * 0.3, 0.0, 1.3)
        rgb = shade(col, 0.42 + 0.66 * b)
        if gp > 0:
            rgb = mix(rgb, (255, 255, 255), gp * 0.28)
        cells.append((kk, ch, rgb))
    return cells


class Stem:
    def __init__(self, tp):
        x0, y0, scale, _s, _z = tp
        bx, by = 357 + (x0 - 357) * 0.12, 812
        ex, ey = x0, y0 + HEAD_B * scale * 0.8
        ctrl = (bx + (ex - bx) * 0.18, by - (by - ey) * 0.45)
        self.pts = bezier((bx, by), ctrl, (ex, ey), 90)

    def cells(self, g):
        n = int(g * (len(self.pts) - 1))
        out, seen = [], set()
        for i in range(n + 1):
            x, y = self.pts[i]
            kk = key_of(int(x // CW), int(y // CH))
            if kk is None or kk in seen:
                continue
            seen.add(kk)
            a = self.pts[max(i - 3, 0)]
            b = self.pts[min(i + 3, len(self.pts) - 1)]
            ch = dir_char(b[0] - a[0], b[1] - a[1])
            k = 0.55 + 0.45 * i / len(self.pts)
            rgb = shade(STEM, k * 1.2)
            if g < 1 and i > n - 6:
                rgb = (200, 255, 176)
            out.append((kk, ch, rgb))
        return out


class Leaf:
    def __init__(self, spec):
        base, ctrl, tip, width = spec
        self.pts = bezier(base, ctrl, tip, 70)
        self.width = width

    def cells(self, g):
        k = max(3, int(g * len(self.pts)))
        pts = self.pts[:k]
        roles = {}
        for i, (x, y) in enumerate(pts):
            uu = i / (k - 1)
            w = self.width * (0.35 + 0.65 * g) * math.sin(math.pi * min(1.0, uu ** 0.85)) ** 0.7
            a = pts[max(i - 2, 0)]
            b = pts[min(i + 2, k - 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / ln, tx / ln
            tt = -w
            while tt <= w + 0.01:
                kk = key_of(int((x + nx * tt) // CW), int((y + ny * tt) // CH))
                if kk is not None:
                    role = 3 if abs(tt) < 3 else 2 if abs(tt) > w - 4.5 else 1
                    prev = roles.get(kk)
                    if prev is None or role > prev[0]:
                        roles[kk] = (role, tx, ty, tt)
                tt += 3.0
        out = []
        for kk, (role, tx, ty, tt) in roles.items():
            r, c = divmod(kk, COLS)
            n = h01(c, r, 5)
            if role == 3:
                ch, rgb = dir_char(tx, ty), mix(LEAF_LIGHT, (170, 230, 150), 0.4)
            elif role == 2:
                ch, rgb = dir_char(tx, ty), shade(LEAF_LIGHT, 1.05)
            else:
                ch = ";" if n < 0.4 else ":" if n < 0.7 else "+" if n < 0.9 else "="
                rgb = shade(LEAF_LIGHT if tt > 0 else LEAF, 0.85 + 0.25 * n)
            if g < 1:
                rgb = mix(rgb, (190, 255, 170), 0.25 * (1 - g))
            out.append((kk, ch, rgb))
        return out


# ------------------------------------------------------------------ dibujo
class Glyphs:
    def __init__(self, font):
        self.font = font
        self.cache = {}

    def get(self, ch, rgb):
        r = int(clamp(rgb[0], 0, 255)) >> 4
        g = int(clamp(rgb[1], 0, 255)) >> 4
        b = int(clamp(rgb[2], 0, 255)) >> 4
        key = (ch, r, g, b)
        hit = self.cache.get(key)
        if hit is None:
            surf = self.font.render(ch, True, ((r << 4) + 8, (g << 4) + 8, (b << 4) + 8))
            hit = (surf, (CW - surf.get_width()) // 2, (CH - surf.get_height()) // 2)
            self.cache[key] = hit
        return hit


def wrap_message(msg, width=34):
    lines = []
    for part in msg.replace("\\n", "|").replace("\n", "|").split("|"):
        part = part.strip()
        while len(part) > width:
            cut = part.rfind(" ", 0, width)
            cut = width if cut <= 0 else cut
            lines.append(part[:cut].strip())
            part = part[cut:].strip()
        lines.append(part)
    return [ln for ln in lines if ln][:3] or [""]


def read_message():
    msg = MESSAGE
    try:
        if WEB:
            import platform as _pf
            search = str(_pf.window.location.search)
            if search.startswith("?"):
                from urllib.parse import parse_qs
                q = parse_qs(search[1:])
                if q.get("msg") and q["msg"][0].strip():
                    msg = q["msg"][0]
        elif len(sys.argv) > 1:
            msg = " ".join(sys.argv[1:])
    except Exception:
        pass
    return msg[:160]


def load_font(size):
    here = os.path.dirname(os.path.abspath(globals().get("__file__", "main.py")))
    for path in (os.path.join(here, FONT_FILE), FONT_FILE):
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size + 4)


class Bouquet:
    def __init__(self, message):
        self.font = load_font(FONT_SIZE)
        self.big = load_font(26)
        self.small = load_font(20)
        self.msg_font = load_font(30)
        self.glyphs = Glyphs(self.font)
        self.lines = wrap_message(message, 34)
        self.msg_len = sum(len(s) for s in self.lines)

        self.tissue = build_tissue()
        self.kraft = build_kraft()
        self.band, self.bow, self.knot = build_twine()
        self.stems = [Stem(tp) for tp in TULIPS]
        self.leaves = [Leaf(sp) for sp in LEAVES]
        self.bloom_rank = {idx: k for k, idx in enumerate(BLOOM_ORDER)}

        self.msg_surf = pygame.Surface((W, 10 + 40 * len(self.lines) + 10))
        self.msg_glow = self.msg_surf.copy()
        self.scene = pygame.Surface((W, H))
        self.glow = pygame.Surface((W, H))
        self.bg = self.make_background()
        self.fly_sprites = self.make_sprites((196, 255, 120), 15)
        self.reset()

    # -------------------------------------------------------- preparación
    def make_background(self):
        bg = pygame.Surface((W, H))
        top, bottom = (8, 7, 20), (26, 10, 30)
        for y in range(H):
            pygame.draw.line(bg, mix(top, bottom, y / H), (0, y), (W, y))
        return bg

    def make_sprites(self, color, radius):
        sprites = []
        size = radius * 2 + 1
        for lvl in range(1, 9):
            s = pygame.Surface((size, size))
            for yy in range(size):
                for xx in range(size):
                    d = math.hypot(xx - radius, yy - radius) / radius
                    k = max(0.0, 1.0 - d) ** 2.2 * lvl / 8
                    s.set_at((xx, yy), shade(color, k))
            sprites.append(s)
        return sprites

    def reset(self):
        self.t = 0.0
        self.cache = {}
        self.msg_key = None
        self.last_tap = -99.0
        self.tapped = False
        self.hearts = []
        self.motes = []
        self.pollen_done = set()
        rnd = random.Random(4)
        self.flies = []
        for _ in range(26):
            self.flies.append({
                "x": rnd.uniform(0, W), "y": rnd.uniform(60, H - 60),
                "a": rnd.uniform(0, 6.28), "sp": rnd.uniform(10, 24),
                "ph": rnd.uniform(0, 6.28), "rate": rnd.uniform(0.6, 1.5),
                "front": rnd.random() < 0.35,
            })

    # ------------------------------------------------------ línea de tiempo
    def tulip_state(self, i, t):
        stem_end = T_STEMS + i * STEM_GAP + STEM_DUR
        sp = window(t, stem_end - 0.2, 0.6)
        k = self.bloom_rank[i]
        cp = window(t, T_COLOR + k * COLOR_GAP, COLOR_DUR)
        raw = window(t, T_BLOOM + k * BLOOM_GAP, BLOOM_DUR)
        op = ease_back(raw) if raw > 0 else 0.0
        gp = math.sin(math.pi * raw) * 0.9 if 0 < raw < 1 else 0.0
        return sp, cp, op, gp

    def layer_specs(self, t):
        specs = []
        p = window(t, *T_TISSUE)
        specs.append((0, "tissue", round(p, 3), lambda p=p: self.tissue_cells(p)))
        for i, st in enumerate(self.stems):
            g = window(t, T_STEMS + i * STEM_GAP, STEM_DUR)
            specs.append((1, "stem%d" % i, round(ease_out(g), 3), lambda g=g, st=st: st.cells(ease_out(g))))
        for j, lf in enumerate(self.leaves):
            g = window(t, T_LEAVES + j * LEAF_GAP, LEAF_DUR)
            specs.append((2, "leaf%d" % j, round(ease_out(g), 3), lambda g=g, lf=lf: lf.cells(ease_out(g))))
        for i, tp in enumerate(TULIPS):
            st = self.tulip_state(i, t)
            key = tuple(round(v, 3) for v in st)
            specs.append((tp[4], "tulip%d" % i, key, lambda st=st, tp=tp: tulip_cells(tp, *st)))
        p = window(t, *T_KRAFT)
        specs.append((6, "kraft", round(p, 3), lambda p=p: self.kraft_cells(p)))
        p = window(t, *T_TWINE)
        boost = clamp(1 - (t - (T_TWINE[0] + T_TWINE[1])) / 0.6) if p >= 1 else 0.0
        specs.append((8, "twine", (round(p, 3), round(boost, 2)), lambda p=p, b=boost: self.twine_cells(p, b)))
        return specs

    def tissue_cells(self, p):
        if p <= 0:
            return []
        yr = lerp(H + 10, 250, ease_out(p))
        out = []
        for kk, y, ch, rgb in self.tissue:
            if y >= yr:
                if p < 1 and y < yr + 30:
                    out.append((kk, "~", mix(rgb, CREAM, 0.75)))
                else:
                    out.append((kk, ch, rgb))
        return out

    def kraft_cells(self, p):
        if p <= 0:
            return []
        xr = lerp(176, 548, ease_in_out(p))
        out = []
        for kk, x, ch, rgb in self.kraft:
            if x <= xr:
                if p < 1 and x > xr - 20:
                    out.append((kk, "|", mix(rgb, CREAM, 0.8)))
                else:
                    out.append((kk, ch, rgb))
        return out

    def twine_cells(self, p, boost):
        if p <= 0:
            return []
        xr = lerp(280, 436, ease_in_out(p))
        out = [(kk, ch, rgb) for kk, x, ch, rgb in self.band if kk is not None and x <= xr]
        if p >= 1:
            col = mix(JUTE, CREAM, 0.3 + 0.7 * boost)
            for kk, ch in self.bow:
                if kk is not None:
                    out.append((kk, ch, (255, 96, 126) if ch in "@\u2665" else col))
        return out

    def draw_message(self, frame):
        t = self.t
        n = int(max(0.0, t - T_MSG) / MSG_RATE)
        if t < T_MSG:
            return
        cursor = t < T_MSG + self.msg_len * MSG_RATE + 1.6 and int(t * 3) % 2 == 0
        key = (min(n, self.msg_len), cursor)
        if key != self.msg_key:
            self.msg_key = key
            self.msg_surf.fill((0, 0, 0))
            adv = self.msg_font.size("M")[0]
            lh = 40
            left = key[0]
            for j, line in enumerate(self.lines):
                x0 = (W - adv * len(line)) // 2
                shown = line[:max(0, left)]
                for i, ch in enumerate(shown):
                    col = (255, 92, 120) if ch == "♥" else MSG_COLOR
                    self.msg_surf.blit(self.msg_font.render(ch, True, col), (x0 + i * adv, 10 + j * lh))
                if left <= len(line):
                    if cursor:
                        self.msg_surf.blit(self.msg_font.render("_", True, CREAM), (x0 + len(shown) * adv, 10 + j * lh))
                    break
                left -= len(line)
            small = pygame.transform.smoothscale(self.msg_surf, (W // 4, self.msg_surf.get_height() // 4))
            if hasattr(pygame.transform, "gaussian_blur"):
                small = pygame.transform.gaussian_blur(small, 2)
            self.msg_glow = pygame.transform.smoothscale(small, self.msg_surf.get_size())
        y = 972 - (len(self.lines) - 1) * 20
        frame.blit(self.msg_glow, (0, y), special_flags=pygame.BLEND_RGB_ADD)
        frame.blit(self.msg_glow, (0, y), special_flags=pygame.BLEND_RGB_ADD)
        frame.blit(self.msg_surf, (0, y), special_flags=pygame.BLEND_RGB_ADD)

    # ------------------------------------------------------------ escena
    def rebuild(self, layers):
        buf = {}
        for _z, cells in sorted(layers, key=lambda L: L[0]):
            for kk, ch, rgb in cells:
                buf[kk] = (ch, rgb)
        seq = []
        get = self.glyphs.get
        for kk, (ch, rgb) in buf.items():
            r, c = divmod(kk, COLS)
            surf, ox, oy = get(ch, rgb)
            seq.append((surf, (c * CW + ox, r * CH + oy)))
        self.scene.fill((0, 0, 0))
        if hasattr(self.scene, "fblits"):
            self.scene.fblits(seq)
        else:
            self.scene.blits(seq, doreturn=False)
        small = pygame.transform.smoothscale(self.scene, (W // 4, H // 4))
        if hasattr(pygame.transform, "gaussian_blur"):
            small = pygame.transform.gaussian_blur(small, 3)
        self.glow = pygame.transform.smoothscale(small, (W, H))
        self.glow.fill((175, 175, 175), special_flags=pygame.BLEND_RGB_MULT)

    def update_scene(self, t):
        dirty = False
        layers = []
        for z, name, key, fn in self.layer_specs(t):
            hit = self.cache.get(name)
            if hit is None or hit[0] != key:
                hit = (key, fn())
                self.cache[name] = hit
                dirty = True
            layers.append((z, hit[1]))
        if dirty:
            self.rebuild(layers)

    def sway(self, t):
        k = smooth(window(t, 8.5, 4.0))
        s = k * (6.5 * math.sin(0.85 * t) + 2.2 * math.sin(2.05 * t + 1.0))
        dt = t - self.last_tap
        if 0 <= dt < 5:
            s += 16 * math.exp(-dt * 1.1) * math.sin(5.2 * dt)
        return s

    # ---------------------------------------------------------- interacción
    def tap(self, x, y):
        self.tapped = True
        self.last_tap = self.t
        rnd = random.Random()
        for _ in range(9):
            self.hearts.append({
                "x": x + rnd.uniform(-30, 30), "y": y + rnd.uniform(-10, 10),
                "vx": rnd.uniform(-40, 40), "vy": rnd.uniform(-170, -70),
                "age": 0.0, "life": rnd.uniform(2.0, 3.2), "ph": rnd.uniform(0, 6.28),
                "col": rnd.choice([(255, 92, 120), (255, 150, 190), (255, 60, 90), (255, 200, 220)]),
                "big": rnd.random() < 0.5,
            })

    # ------------------------------------------------------------ cuadro
    def step(self, dt):
        self.t += dt
        t = self.t
        for i, tp in enumerate(TULIPS):
            k = self.bloom_rank[i]
            if i not in self.pollen_done and t >= T_BLOOM + k * BLOOM_GAP + 0.15:
                self.pollen_done.add(i)
                rnd = random.Random(i * 31 + int(t * 10))
                for _ in range(7):
                    self.motes.append({
                        "x": tp[0] + rnd.uniform(-20, 20), "y": tp[1] - 30 + rnd.uniform(-8, 8),
                        "vx": rnd.uniform(-16, 16), "vy": rnd.uniform(-46, -18),
                        "age": 0.0, "life": rnd.uniform(1.6, 2.8),
                        "ch": rnd.choice("·.*'"),
                    })
        for m in self.motes:
            m["age"] += dt
            m["x"] += m["vx"] * dt
            m["y"] += m["vy"] * dt
            m["vy"] *= 0.99
        self.motes = [m for m in self.motes if m["age"] < m["life"]]
        for h in self.hearts:
            h["age"] += dt
            h["x"] += (h["vx"] + 30 * math.sin(h["ph"] + h["age"] * 3)) * dt
            h["y"] += h["vy"] * dt
            h["vy"] *= 0.995
        self.hearts = [h for h in self.hearts if h["age"] < h["life"]]
        for f in self.flies:
            f["a"] += math.sin(t * 0.7 + f["ph"]) * 1.4 * dt
            f["x"] = (f["x"] + math.cos(f["a"]) * f["sp"] * dt) % W
            f["y"] += math.sin(f["a"]) * f["sp"] * dt
            if f["y"] < 30 or f["y"] > H - 30:
                f["a"] = -f["a"]
                f["y"] = clamp(f["y"], 30, H - 30)

    def draw_flies(self, frame, front):
        fade = smooth(self.t / 2.0)
        for f in self.flies:
            if f["front"] != front:
                continue
            b = (0.5 + 0.5 * math.sin(f["ph"] + self.t * f["rate"] * 2.2)) ** 3 * fade
            lvl = int(b * 7.99)
            if lvl > 0:
                spr = self.fly_sprites[lvl]
                frame.blit(spr, (int(f["x"]) - spr.get_width() // 2, int(f["y"]) - spr.get_height() // 2),
                           special_flags=pygame.BLEND_RGB_ADD)

    def draw_particles(self, frame):
        for m in self.motes:
            a = 1 - m["age"] / m["life"]
            surf, ox, oy = self.glyphs.get(m["ch"], (255, 222, 130))
            surf.set_alpha(int(255 * a))
            frame.blit(surf, (int(m["x"]), int(m["y"])))
            surf.set_alpha(255)
        for h in self.hearts:
            a = clamp(1 - h["age"] / h["life"]) * clamp(h["age"] * 6)
            key = ("heart", h["col"], h["big"])
            surf = self.glyphs.cache.get(key)
            if surf is None:
                surf = (self.big if h["big"] else self.font).render("♥", True, h["col"])
                self.glyphs.cache[key] = surf
            surf.set_alpha(int(255 * a))
            frame.blit(surf, (int(h["x"]) - surf.get_width() // 2, int(h["y"]) - surf.get_height() // 2))
            surf.set_alpha(255)

    def draw_hint(self, frame):
        t0 = T_MSG + self.msg_len * MSG_RATE + 2.0
        if self.tapped or self.t < t0:
            return
        a = smooth((self.t - t0) / 1.5) * (0.35 + 0.25 * math.sin(self.t * 2.2))
        key = ("hint",)
        surf = self.glyphs.cache.get(key)
        if surf is None:
            surf = self.small.render("toca la pantalla ♥", True, (220, 170, 200))
            self.glyphs.cache[key] = surf
        surf.set_alpha(int(255 * a))
        frame.blit(surf, ((W - surf.get_width()) // 2, H - 40))

    def draw(self, frame):
        t = self.t
        self.update_scene(t)
        frame.blit(self.bg, (0, 0))
        self.draw_flies(frame, front=False)
        sw = self.sway(t)
        span = TIP[1] - SWAY_TOP
        for r in range(ROWS):
            y = r * CH
            f = clamp((TIP[1] - (y + CH / 2)) / span) ** 1.5
            dx = int(round(sw * f))
            area = pygame.Rect(0, y, W, CH)
            frame.blit(self.glow, (dx, y), area, special_flags=pygame.BLEND_RGB_ADD)
            frame.blit(self.scene, (dx, y), area, special_flags=pygame.BLEND_RGB_ADD)
        self.draw_message(frame)
        self.draw_particles(frame)
        self.draw_flies(frame, front=True)
        self.draw_hint(frame)


# ---------------------------------------------------------------- programa
async def main():
    pygame.init()
    pygame.display.set_caption("tulipanes")
    if WEB:
        screen = pygame.display.set_mode((W, H))
        scale = 1.0
    else:
        try:
            dh = pygame.display.get_desktop_sizes()[0][1]
        except Exception:
            dh = H + 100
        scale = min(1.0, (dh - 110) / H)
        screen = pygame.display.set_mode((int(W * scale), int(H * scale)))
    frame = pygame.Surface((W, H)) if scale < 1.0 else screen

    bouquet = Bouquet(read_message())
    clock = pygame.time.Clock()
    paused = False
    running = True
    shots = 0
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE and not WEB:
                    running = False
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_r:
                    bouquet.reset()
                elif e.key == pygame.K_s and not WEB:
                    shots += 1
                    pygame.image.save(frame, "tulipanes_%02d.png" % shots)
            elif e.type == pygame.MOUSEBUTTONDOWN:
                # en celulares SDL convierte el toque en clic, así que basta con esto
                bouquet.tap(e.pos[0] / scale, e.pos[1] / scale)
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        if not paused:
            bouquet.step(dt)
        bouquet.draw(frame)
        if frame is not screen:
            pygame.transform.smoothscale(frame, screen.get_size(), screen)
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
