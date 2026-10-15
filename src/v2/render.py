"""Render de la v2: loop de 30 s a 60 fps.

Capas, de abajo hacia arriba:
  1. La ilustración original (zona del reloj un poco más tenue).
  2. Sus elementos animados: estrellas que titilan, corazones que laten,
     Géminis y Capricornio que brillan por turnos, ola de luz en los caminos.
  3. Cometas que recorren los caminos punteados que ella dibujó.
  4. Constelaciones que se dibujan solas: J ♥ C, TE AMO, 18·10·25.
  5. Morse: una estrella del dibujo parpadea "TE AMO".
  6. Polvo de estrellas flotando.

Todo es periódico en T, así que el loop no tiene corte.
"""
import math, os, pickle
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd
from glyphs import layout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FPS, T = 60, 30.0
N = int(FPS * T)

GLOW = np.array([255, 175, 140], np.float32) / 255
GOLD = np.array([255, 215, 170], np.float32) / 255
WHITE = np.array([255, 238, 215], np.float32) / 255

MESSAGES = [  # texto, alto de letra, centro y, inicio (s)
    ("J♥C", 215, 1090, 2.5),
    ("TE AMO", 150, 1170, 12.5),
    ("18·10·25", 118, 1250, 22.0),
]
DRAW, HOLD, FADE = 2.4, 3.4, 1.6

MORSE_TEXT = "TE AMO"
MORSE = {"T": "-", "E": ".", "A": ".-", "M": "--", "O": "---"}


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def gauss_sprite(sig):
    r = int(sig * 3.5) + 1
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return np.exp(-(xx ** 2 + yy ** 2) / (2 * sig * sig)).astype(np.float32)


def flare_sprite(rad):
    """Estrella de 4 puntas como las que ella dibuja."""
    r = int(rad)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    ax, ay = np.abs(xx), np.abs(yy)
    f = (np.exp(-ax / 1.1) * np.exp(-ay / (rad * 0.42)) + np.exp(-ay / 1.1) * np.exp(-ax / (rad * 0.42))
         + 1.4 * np.exp(-(xx ** 2 + yy ** 2) / (rad * 0.18) ** 2))
    return (f / f.max()).astype(np.float32)


def blit(F, cy, cx, spr, color, amp):
    """Suma un sprite centrado en (cy, cx), recortando en los bordes."""
    H, W, _ = F.shape
    r = spr.shape[0] // 2
    y0, x0 = int(round(cy)) - r, int(round(cx)) - r
    ya, xa = max(y0, 0), max(x0, 0)
    yb, xb = min(y0 + spr.shape[0], H), min(x0 + spr.shape[1], W)
    if ya >= yb or xa >= xb:
        return
    F[ya:yb, xa:xb] += (spr[ya - y0:yb - y0, xa - x0:xb - x0] * amp)[..., None] * color


class Scene:
    def __init__(self):
        D = pickle.load(open(os.path.join(ROOT, "build", "seg_v2.pkl"), "rb"))
        im, bg, ink, lab, comps = D["im"], D["bg"], D["ink"], D["lab"], D["comps"]
        self.H, self.W = H, W = im.shape[:2]
        rng = np.random.default_rng(2025)
        res = im - bg
        ys = np.arange(H, dtype=np.float32)
        # zona del reloj (arriba): efectos más suaves para que se lea la hora
        self.zone = lambda y: 0.45 + 0.55 * smooth((y - 300) / 500)

        # estrella del morse: una de las grandes, abajo a la derecha, escondida entre las demás
        sparks = [i for i, c in enumerate(comps) if c["k"] == "spark" and c["area"] > 250]
        self.morse_id = min(sparks, key=lambda i: (comps[i]["cx"] - 800) ** 2 + (comps[i]["cy"] - 1880) ** 2)

        self.items = []
        for i, c in enumerate(comps):
            k = c["k"]
            if k == "dot" and c["area"] < 12:
                continue
            m = {"heart": 40, "sign": 30, "spark": 26, "line": 12, "dot": 8}[k]
            sl0 = c["sl"]
            sl = (slice(max(sl0[0].start - m, 0), min(sl0[0].stop + m, H)),
                  slice(max(sl0[1].start - m, 0), min(sl0[1].stop + m, W)))
            msk = nd.binary_dilation(lab[sl] == i + 1, iterations=2)
            a = (ink[sl] * msk).astype(np.float32)
            blur = nd.gaussian_filter(a, {"heart": 14, "sign": 12, "spark": 8, "line": 5, "dot": 4}[k])
            blur /= max(blur.max(), 1e-3)
            h, w = sl0[0].stop - sl0[0].start, sl0[1].stop - sl0[1].start
            it = dict(k=k, sl=sl, r=res[sl] * msk[..., None], blur=blur, cy=c["cy"], cx=c["cx"],
                      ph=rng.random(), z=self.zone(c["cy"]), morse=(i == self.morse_id))
            if k == "spark":
                it["f"] = int(rng.integers(2, 6))
                it["big"] = c["area"] > 250
                it["flare"] = flare_sprite(max(h, w) * 0.75)
            elif k == "heart":
                it["f"] = int(rng.integers(5, 8))
            elif k == "sign":
                # Géminis (relleno sólido tras cerrar huecos) vs Capricornio: brillan por turnos
                it["gemini"] = c["area"] / (h * w) > 0.6
            else:
                it["f"] = int(rng.integers(2, 5))
            self.items.append(it)
        self.hearts = [it for it in self.items if it["k"] == "heart"]

        top = (0.86 + 0.14 * np.clip(ys / 700, 0, 1))[:, None, None]
        base = im.copy()
        for h_ in self.hearts:
            base[h_["sl"]] -= h_["r"]
        self.base = base * top

        # caminos para cometas
        self.paths = []
        for p in D["paths"]:
            sl = p["sl"]
            valid = ~np.isnan(p["smap"])
            self.paths.append(dict(p, r=res[sl] * valid[..., None], smap=np.nan_to_num(p["smap"], nan=1e9)))
        longs = sorted(range(len(self.paths)), key=lambda j: -self.paths[j]["length"])
        order = rng.permutation(longs[:12])
        self.comets = []
        for n in range(8):
            j = int(order[n % len(order)])
            L = self.paths[j]["length"]
            self.comets.append(dict(t0=0.8 + n * 3.75, j=j, rev=bool(rng.random() < 0.5),
                                    dur=float(np.clip(L / 360, 1.1, 3.4))))
        self.spr_head = gauss_sprite(4.5)
        self.spr_tail = gauss_sprite(2.2)
        self.flare_head = flare_sprite(16)

        self._init_messages(rng)
        self._init_morse()

        NP = 90
        self.P = dict(x=rng.uniform(0, W, NP), y=rng.uniform(0, H, NP), k=rng.integers(2, 5, NP),
                      ph=rng.random(NP), dr=rng.uniform(80, 240, NP), sw=rng.uniform(10, 30, NP))
        self.P_spr = [gauss_sprite(s) for s in rng.uniform(1.4, 3.6, NP)]

    # ---------- constelaciones ----------
    def _init_messages(self, rng):
        self.msgs = []
        for text, hgt, cy, t0 in MESSAGES:
            strokes = layout(text, hgt, self.W / 2, cy)
            segs, stars, cum = [], {}, 0.0
            for s in strokes:
                ends = (s[0], s[-1])
                for q in s:
                    key = (round(q[0]), round(q[1]))
                    if key not in stars:
                        stars[key] = dict(p=q, s=cum, end=q in ends or len(s) == 1, ph=rng.random())
                for a, b in zip(s, s[1:]):
                    L = math.dist(a, b)
                    segs.append((a, b, cum, L))
                    cum += L
                    key = (round(b[0]), round(b[1]))
                    stars[key]["s"] = min(stars[key]["s"], cum)
            xs = [q[0] for s in strokes for q in s]
            yy = [q[1] for s in strokes for q in s]
            m = 50
            box = (int(min(xs)) - m, int(min(yy)) - m, int(max(xs)) + m, int(max(yy)) + m)
            # halo oscuro suave detrás del mensaje para que se lea
            Y, X = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
            ex = ((X - self.W / 2) / ((box[2] - box[0]) * 0.62)) ** 2 + ((Y - cy) / ((box[3] - box[1]) * 0.85)) ** 2
            halo = np.exp(-ex * 1.6)
            sl = (slice(max(int(cy - 3 * hgt), 0), min(int(cy + 3 * hgt), self.H)), slice(0, self.W))
            self.msgs.append(dict(t0=t0, segs=segs, stars=list(stars.values()), L=cum, box=box,
                                  halo=halo[sl][..., None], halo_sl=sl))
        self.star_big = flare_sprite(22) + 0.6 * np.pad(gauss_sprite(3.2), 22 - gauss_sprite(3.2).shape[0] // 2)
        self.star_small = flare_sprite(13) + 0.5 * np.pad(gauss_sprite(2.4), 13 - gauss_sprite(2.4).shape[0] // 2)
        self.pen = gauss_sprite(5)

    def _draw_message(self, F, msg, t):
        dt = (t - msg["t0"]) % T
        life = DRAW + HOLD + FADE
        if dt > life + 0.6:
            return
        alpha = smooth(dt / 0.6) * (1 - smooth((dt - DRAW - HOLD) / FADE))
        if alpha <= 0:
            return
        F[msg["halo_sl"]] *= 1 - 0.28 * alpha * msg["halo"]
        p = smooth(dt / DRAW)
        Lp = p * msg["L"]
        x0, y0, x1, y1 = msg["box"]
        S = 3
        canvas = Image.new("L", ((x1 - x0) * S, (y1 - y0) * S), 0)
        d = ImageDraw.Draw(canvas)
        pen_at = None
        for a, b, c0, L in msg["segs"]:
            if c0 >= Lp:
                break
            f = min((Lp - c0) / L, 1.0)
            e = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            d.line([((a[0] - x0) * S, (a[1] - y0) * S), ((e[0] - x0) * S, (e[1] - y0) * S)], fill=255, width=S * 2)
            if f < 1:
                pen_at = e
        lines = np.asarray(canvas.resize((x1 - x0, y1 - y0), Image.BOX), np.float32) / 255
        glow = nd.gaussian_filter(lines, 6)
        F[y0:y1, x0:x1] += (lines * 140 * alpha)[..., None] * GOLD + (glow * 170 * alpha)[..., None] * GLOW
        for st in msg["stars"]:
            ap = smooth((Lp - st["s"] + 1) / 35)
            if ap <= 0:
                continue
            tw = 0.72 + 0.28 * math.sin(2 * math.pi * (4 * t / T + st["ph"]))
            pop = 1 + 0.8 * math.exp(-((Lp - st["s"]) / 40) ** 2)  # destello al aparecer
            spr = self.star_big if st["end"] else self.star_small
            blit(F, st["p"][1], st["p"][0], spr, WHITE, 230 * alpha * ap * tw * pop)
        if pen_at is not None:
            blit(F, pen_at[1], pen_at[0], self.pen, WHITE, 200 * alpha)

    # ---------- morse ----------
    def _init_morse(self):
        units = []
        for wi, word in enumerate(MORSE_TEXT.split(" ")):
            for li, ch in enumerate(word):
                for si, sym in enumerate(MORSE[ch]):
                    units += [1] * (1 if sym == "." else 3)
                    if si < len(MORSE[ch]) - 1:
                        units += [0]
                if li < len(word) - 1:
                    units += [0] * 3
            units += [0] * 7
        reps = 2  # el mensaje se repite dos veces por loop
        self.morse_units = np.array(units, np.float32)
        self.morse_unit = T / reps / len(units)
        print(f"morse: {len(units)} unidades, unidad = {self.morse_unit:.3f}s")

    def morse_level(self, t):
        u = (t / self.morse_unit) % len(self.morse_units)
        i = int(u)
        on = self.morse_units[i]
        # bordes suaves de ~40 ms
        frac = u - i
        edge = 0.04 / self.morse_unit
        prv = self.morse_units[i - 1]
        if frac < edge:
            return float(prv + (on - prv) * smooth(frac / edge))
        return float(on)

    # ---------- frame ----------
    def frame(self, n):
        t = n / FPS
        F = self.base.copy()
        wave_y = -500 + (self.H + 1000) * ((2 * t / T) % 1)
        lit = {}
        for it in self.items:
            k, sl, z = it["k"], it["sl"], it["z"]
            wave = math.exp(-((it["cy"] - wave_y) / 260) ** 2)
            if it["morse"]:
                m = self.morse_level(t)
                F[sl] += it["r"] * (0.2 + 1.6 * m) + (it["blur"] * (25 + 110 * m))[..., None] * GLOW
                blit(F, it["cy"], it["cx"], it["flare"], WHITE, 210 * m)
            elif k == "spark":
                u = (it["f"] * t / T + it["ph"]) % 1
                tw = math.sin(math.pi * u) ** 10
                F[sl] += it["r"] * (z * (0.45 * tw + 0.5 * wave) * 1.2) + \
                    (it["blur"] * z * (0.45 * tw + 0.3 * wave) * 70)[..., None] * GLOW
                if it["big"]:
                    blit(F, it["cy"], it["cx"], it["flare"], GOLD, 120 * tw * z)
            elif k == "heart":
                u = (it["f"] * t / T + it["ph"]) % 1
                b = math.exp(-(u / 0.022) ** 2) + 0.65 * math.exp(-((u - 0.08) / 0.025) ** 2) + math.exp(-((u - 1) / 0.022) ** 2)
                sc = 1 + 0.07 * b
                h, w = it["r"].shape[:2]
                out = np.empty_like(it["r"])
                for ch in range(3):
                    a = np.asarray(Image.fromarray(it["r"][..., ch]).resize((round(w * sc), round(h * sc)), Image.BICUBIC))
                    oy, ox = (a.shape[0] - h) // 2, (a.shape[1] - w) // 2
                    out[..., ch] = a[oy:oy + h, ox:ox + w]
                F[sl] += out * (1 + z * (0.5 * b + 0.4 * wave)) + (it["blur"] * z * (0.5 * b + 0.3 * wave) * 80)[..., None] * GLOW
            elif k == "sign":
                ph = 0.0 if it["gemini"] else 0.5
                br = 0.5 + 0.5 * math.sin(2 * math.pi * (3 * t / T + ph))
                F[sl] += it["r"] * z * (0.3 * br + 0.7 * wave) + (it["blur"] * z * (0.3 * br + 0.6 * wave) * 60)[..., None] * GLOW
            else:
                u = (it["f"] * t / T + it["ph"]) % 1
                g = 0.9 * wave + (0.3 * math.sin(math.pi * u) ** 6 if k == "dot" else 0)
                F[sl] += it["r"] * g * 1.3 * z + (it["blur"] * g * z * 50)[..., None] * GLOW

        for c in self.comets:
            self._draw_comet(F, c, t)
        for msg in self.msgs:
            self._draw_message(F, msg, t)

        P = self.P
        for i in range(len(P["x"])):
            u = (P["k"][i] * t / T + P["ph"][i]) % 1
            al = math.sin(math.pi * u) ** 2
            y = P["y"][i] - P["dr"][i] * u
            x = P["x"][i] + P["sw"][i] * math.sin(2 * math.pi * u)
            blit(F, y, x, self.P_spr[i], GOLD, 120 * al * self.zone(y))
        return np.clip(F, 0, 255).astype(np.uint8)

    def _draw_comet(self, F, c, t):
        dt = (t - c["t0"]) % T
        tail_fade = 1.2
        if dt > c["dur"] + tail_fade:
            return
        p = self.paths[c["j"]]
        L = p["length"]
        s_head = L * min(dt / c["dur"], 1.0)
        fade = smooth(dt / 0.25) * (1 - smooth((dt - c["dur"]) / tail_fade))
        head_vis = 1 - smooth((dt - c["dur"] + 0.15) / 0.3)
        smap = L - p["smap"] if c["rev"] else p["smap"]
        lag = s_head - smap
        gain = np.where((lag >= 0) & (lag < 1e8), np.exp(-np.maximum(lag, 0) / 170), 0).astype(np.float32) * fade
        z = self.zone(p["sl"][0].start + p["smap"].shape[0] / 2)
        F[p["sl"]] += p["r"] * (2.4 * gain * z)[..., None] + (nd.gaussian_filter(gain * (p["r"].mean(2) > 1), 5) * 120 * z)[..., None] * GLOW
        path, s = p["path"], p["s"]
        sp = (L - s_head) if c["rev"] else s_head

        def at(sv):
            j = int(np.clip(np.searchsorted(s, sv), 0, len(s) - 1))
            return path[j]
        if head_vis > 0:
            for d in range(0, 170, 5):
                sv = sp + d if c["rev"] else sp - d
                if 0 <= sv <= L:
                    q = at(sv)
                    blit(F, q[0], q[1], self.spr_tail, GOLD, 120 * (1 - d / 170) ** 2 * head_vis * z)
            q = at(sp)
            blit(F, q[0], q[1], self.spr_head, WHITE, 230 * head_vis * fade * z)
            blit(F, q[0], q[1], self.flare_head, WHITE, 150 * head_vis * fade * z)
