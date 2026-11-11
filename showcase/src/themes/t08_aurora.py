"""08 · Aurora boreal: cortinas de luz sobre montañas, reflejadas en un lago.

Personalizable: nombres y la frase.
Sorpresa (Navidad): nieva, la aurora se tiñe de rojo y dice "Feliz Navidad, mi amor".
"""
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw
from common import (W, H, T, TAU, Patch, add, blit, blur, gauss_sprite, hexc, text_mask, vgrad, vignette, finish)

TITLE = "Aurora boreal"
CAPTION = "Una aurora boreal solo para ustedes dos"
SPECIAL = "En Navidad, nieva y la aurora se pinta de rojo"

if W > H:   # escritorio: todo más bajo y extendido a lo ancho
    LAKE, RIDGE1, RIDGE2, AMP, TREE = 760, 610, 700, 0.5, (14, 42)
    CURTAINS = ((330, 230, -0.16, 1.0, 1, 2), (230, 170, 0.12, 0.6, 1, -1), (420, 120, -0.04, 0.45, -1, 2))
    NAMES_Y, SUB_Y = 880, 950
else:
    LAKE, RIDGE1, RIDGE2, AMP, TREE = 1560, 1300, 1440, 1.0, (25, 85)
    CURTAINS = ((860, 320, -0.38, 1.0, 1, 2), (720, 240, 0.28, 0.6, 1, -1), (990, 170, -0.08, 0.45, -1, 2))
    NAMES_Y, SUB_Y = 1870, 1960
SH, SW = LAKE // 4, W // 4    # resolución a la que se calcula la aurora (1/4)


class Theme:
    def __init__(self, special=False):
        self.special = special
        rng = np.random.default_rng(8)
        self.sky = vgrad([(0, "#01030c"), (0.35, "#04122a"), (0.6, "#08263a"), (LAKE / H, "#0d3440"), (1, "#0d3440")])
        self.stars = [(rng.uniform(0, LAKE - 200 * AMP), rng.uniform(0, W), rng.uniform(0.15, 0.6), rng.uniform(0, TAU),
                       int(rng.integers(1, 4))) for _ in range(int(260 * W * H / 1080 / 2340))]

        # montañas (dos capas) y pinos en la orilla
        far = Image.new("L", (W, H), 0)
        xs = np.arange(0, W + 20, 10)
        r1 = RIDGE1 + AMP * (90 * np.sin(xs / 210 + 1) + 60 * np.sin(xs / 77) + np.cumsum(rng.normal(0, 6, len(xs))))
        ImageDraw.Draw(far).polygon([(0, LAKE)] + [(int(a), int(b)) for a, b in zip(xs, r1)] + [(W, LAKE)], fill=255)
        self.far = blur(np.asarray(far, np.float32) / 255, 1.2)[:LAKE]
        img = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(img)
        r2 = RIDGE2 + AMP * (50 * np.sin(xs / 140 + 3) + 30 * np.sin(xs / 41) + np.cumsum(rng.normal(0, 4, len(xs))))
        d.polygon([(0, LAKE)] + [(int(a), int(b)) for a, b in zip(xs, r2)] + [(W, LAKE)], fill=255)
        for x0 in np.arange(-10, W + 10, 14):
            h = rng.uniform(*TREE)
            d.polygon([(x0 - h * 0.22, LAKE + 1), (x0, LAKE - h), (x0 + h * 0.22, LAKE + 1)], fill=255)
        self.mount = blur(np.asarray(img, np.float32) / 255, 0.8)[:LAKE]

        yy = np.linspace(0, LAKE, SH, dtype=np.float32)[:, None]
        xx = np.linspace(0, W, SW, dtype=np.float32)[None, :]
        self.yy, self.xx = yy, xx
        self.curtains = [dict(y=y0, h=h, sl=sl, a1=rng.uniform(55, 90), l1=rng.uniform(700, 1100), k1=int(k1),
                              a2=rng.uniform(6, 12), l2=rng.uniform(140, 220), k2=int(k2), ph=rng.uniform(0, TAU),
                              amp=amp)
                         for y0, h, sl, amp, k1, k2 in CURTAINS]
        self.ray_ph = rng.uniform(0, TAU, 3)

        base_txt = np.zeros((H, W, 3), np.float32)
        sub = "Feliz Navidad, mi amor" if special else "bajo el mismo cielo"
        self.names = Patch(text_mask("DANIELA & MATEO", "mont", 44, cy=NAMES_Y, wght=500, tracking=14))
        self.sub = Patch(text_mask(sub, "playfair-i", 50, cy=SUB_Y, wght=400))
        ripple = np.arange(H - LAKE, dtype=np.float32)
        self.rip_y = ripple
        self.map_x = np.tile(np.arange(W, dtype=np.float32), (H - LAKE, 1))
        self.flakes = [(rng.uniform(0, W), rng.random(), int(rng.integers(1, 3)), rng.uniform(0.8, 2.6),
                        rng.uniform(0, TAU)) for _ in range(int(200 * W / 1080))]

    def aurora(self, t):
        a = TAU * t / T
        yy, xx = self.yy, self.xx
        I = np.zeros((SH, SW), np.float32)
        top = np.zeros((SH, SW), np.float32)
        for i, c in enumerate(self.curtains):
            b = (c["y"] + c["sl"] * (xx - W / 2) + c["a1"] * np.sin(TAU * xx / c["l1"] + c["k1"] * a + c["ph"])
                 + c["a2"] * np.sin(TAU * xx / c["l2"] + c["k2"] * a * 2))
            up = b - yy
            body = np.where(up > 0, np.exp(-up / c["h"]) * 0.95, np.exp(-(up / 30) ** 2) * 0.95)
            body += np.exp(-((up - 12) / 20) ** 2) * 0.5          # borde inferior brillante
            rays = 0.45 + 0.55 * (np.sin(xx * (0.07 + 0.03 * i) + 3 * np.sin(xx * 0.013 + a * (i + 1)) + self.ray_ph[i]) ** 2
                                  * (0.6 + 0.4 * np.sin(xx * 0.031 - a * 2 + i)))
            breathe = 0.8 + 0.2 * math.sin(a * (i + 1) + i)
            I += body * rays * c["amp"] * breathe
            top += body * rays * c["amp"] * np.clip(up / c["h"], 0, 1.5)
        return I, top

    def frame(self, t):
        a = TAU * t / T
        F = self.sky.copy()
        for y, x, amp, ph, k in self.stars:
            blit(F, gauss_sprite(1.0), y, x, hexc("#e8f0ff"), amp * (0.7 + 0.3 * math.sin(k * a + ph)))

        I, top = self.aurora(t)
        I = cv2.resize(I, (W, LAKE), interpolation=cv2.INTER_CUBIC)
        top = cv2.resize(top, (W, LAKE), interpolation=cv2.INTER_CUBIC)
        mix = np.clip(top / (I + 1e-3), 0, 1)[..., None]
        if self.special:
            low, high = hexc("#4dffa6"), hexc("#ff3d6e")
        else:
            low, high = hexc("#4dffb0"), hexc("#9b5cff")
        col = low * (1 - mix) + high * mix
        sky = F[:LAKE]
        sky += np.clip(I, 0, 2)[..., None] * col * 0.55
        m = self.far[..., None]
        sky *= 1 - m
        sky += m * hexc("#0a1b29")
        m = self.mount[..., None]
        sky *= 1 - m
        sky += m * hexc("#03070d")

        # lago: espejo del cielo con ondas
        rows = np.clip(2 * LAKE - np.arange(LAKE, H), 0, LAKE - 1)
        refl = F[rows]
        shift = (3 * np.sin(self.rip_y * 0.09 + a * 3) + 1.5 * np.sin(self.rip_y * 0.23 - a * 5)) * (0.3 + self.rip_y / 1200)
        refl = cv2.remap(refl, self.map_x + shift[:, None], np.tile(np.arange(H - LAKE, dtype=np.float32)[:, None], (1, W)),
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        F[LAKE:] = refl * 0.55 + hexc("#02080e") * 0.4
        F[LAKE:LAKE + 2] += 0.08

        add(F, self.names, hexc("#eaf7ff"), 0.92)
        add(F, self.sub, hexc("#b8ffe0") if not self.special else hexc("#ffd6df"), 0.85)

        if self.special:
            for x0, y0, k, s, ph in self.flakes:
                u = (y0 + k * t / T) % 1
                blit(F, gauss_sprite(round(s * 2) / 2), -20 + u * (H + 40), x0 + 25 * math.sin(TAU * u * 3 + ph),
                     hexc("#ffffff"), 0.35 + 0.25 * s / 2.6)
        F *= vignette(0.4)
        return finish(F)
