"""04 · Luciérnagas: en un bosque de noche, las luciérnagas se juntan y escriben sus nombres.

Personalizable: nombres y la frase.
Sorpresa (aniversario): forman los años que cumplen juntos y un corazón.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from common import (W, H, T, TAU, Patch, add, blit, blur, gauss_sprite, glow_patch, heart_mask, hexc,
                    spread_points, sm, text_mask, vgrad, vignette, window, finish)

TITLE = "Luciérnagas"
CAPTION = "Cientos de luciérnagas escriben sus nombres"
SPECIAL = "En su aniversario escriben los años juntos"

CORE = hexc("#f4ffc4")
GLOW = hexc("#a8ff3e")


def tree(d, x, y, ang, length, width, depth, rng):
    if depth == 0 or length < 8:
        return
    x2, y2 = x + length * math.cos(ang), y - length * math.sin(ang)
    d.line((x, y, x2, y2), fill=255, width=max(int(width), 1))
    n = 2 if rng.random() < 0.8 else 3
    for _ in range(n):
        tree(d, x2, y2, ang + rng.uniform(-0.65, 0.65), length * rng.uniform(0.62, 0.8), width * 0.68, depth - 1, rng)


class Theme:
    def __init__(self, special=False):
        self.special = special
        rng = np.random.default_rng(4)
        F = vgrad([(0, "#010309"), (0.45, "#041019"), (0.8, "#08201a"), (1, "#030a07")])
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        F += np.exp(-((x - 860) ** 2 + (y - 420) ** 2) / (2 * 260 ** 2))[..., None] * hexc("#3a5a6a") * 0.35
        for _ in range(160):
            blit(F, gauss_sprite(0.8), rng.uniform(0, 1100), rng.uniform(0, W), hexc("#dfe8ff"), rng.uniform(0.1, 0.4))

        # bosque: fila lejana borrosa, árboles a los lados y pasto al frente
        far = Image.new("L", (W, H), 0)
        df = ImageDraw.Draw(far)
        xs = np.arange(0, W + 40, 40)
        top = 1820 + 60 * np.sin(xs / 90) + rng.uniform(-60, 40, len(xs))
        df.polygon([(0, H)] + [(int(a), int(b)) for a, b in zip(xs, top)] + [(W, H)], fill=255)
        for xx in rng.uniform(0, W, 18):
            h = rng.uniform(150, 320)
            df.polygon([(xx - 40, 1900), (xx, 1900 - h), (xx + 40, 1900)], fill=255)
        far = blur(np.asarray(far, np.float32) / 255, 4)
        F = F * (1 - far[..., None]) + far[..., None] * hexc("#06150f")

        near = Image.new("L", (W, H), 0)
        dn = ImageDraw.Draw(near)
        tree(dn, 40, H, math.radians(84), 420, 46, 9, rng)
        tree(dn, 1050, H, math.radians(97), 380, 40, 9, rng)
        for xx in np.arange(-10, W + 10, 7):
            h = rng.uniform(60, 190)
            lean = rng.uniform(-30, 30)
            dn.polygon([(xx - 5, H), (xx + lean, H - h), (xx + 5, H)], fill=255)
        near = blur(np.asarray(near, np.float32) / 255, 1)
        F = F * (1 - near[..., None]) + near[..., None] * hexc("#010302")
        F *= vignette(0.5)
        self.base = F

        # a dónde van las que escriben
        if special:
            m = np.maximum(text_mask("5 años", "dancing", 230, cy=1150, wght=700),
                           heart_mask(200, cx=540, cy=1460, w=W, h=H, outline=16))
            sub = "y los que faltan"
        else:
            m = text_mask("Fer & Pau", "dancing", 220, cy=1230, wght=700)
            sub = "nuestro primer verano · 2017"
        self.n_text = 240 if special else 210
        self.targets = spread_points(m, self.n_text, rng)
        self.halo = glow_patch(m, 18)
        self.sub = Patch(text_mask(sub, "mont", 30, cy=1500 if not special else 1680, wght=400, tracking=6))

        n = self.n_text + 70
        self.home = np.stack([rng.uniform(650, 2150, n), rng.uniform(30, W - 30, n)], -1)
        self.amp = rng.uniform(30, 110, (n, 2))
        self.k = rng.integers(1, 3, (n, 2))
        self.ph = rng.uniform(0, TAU, (n, 4))
        self.bk = rng.integers(2, 6, n)
        # cada una llega con un pequeño retraso distinto
        self.delay = rng.uniform(0, 0.9, n)

    def frame(self, t):
        F = self.base.copy()
        a = TAU * t / T
        wy = self.home[:, 0] + self.amp[:, 0] * np.sin(self.k[:, 0] * a + self.ph[:, 0])
        wx = self.home[:, 1] + self.amp[:, 1] * np.sin(self.k[:, 1] * a + self.ph[:, 1])
        blink = (0.5 + 0.5 * np.sin(self.bk * a + self.ph[:, 2])) ** 3

        w = np.zeros(len(wy))
        nt = self.n_text
        w[:nt] = sm((t - 2.0 - self.delay[:nt]) / 1.4) * sm((8.6 - self.delay[:nt] * 0.5 - t) / 1.2)
        ty = np.zeros_like(wy)
        tx = np.zeros_like(wx)
        ty[:nt] = self.targets[:, 0] + 3 * np.sin(3 * a + self.ph[:nt, 3])
        tx[:nt] = self.targets[:, 1] + 3 * np.cos(2 * a + self.ph[:nt, 3])
        py = wy * (1 - w) + ty * w
        px = wx * (1 - w) + tx * w
        bright = blink * (1 - w) + (0.8 + 0.2 * blink) * w

        g = float(np.mean(w[:nt]))
        add(F, self.halo, GLOW, 0.16 * g)
        add(F, self.sub, CORE, 0.75 * sm((g - 0.6) / 0.3))
        halo, core = gauss_sprite(10.0), gauss_sprite(2.2)
        for yy, xx, b in zip(py, px, bright):
            if b < 0.02:
                continue
            blit(F, halo, yy, xx, GLOW, 0.22 * b)
            blit(F, core, yy, xx, CORE, 0.9 * b)
        return finish(F)
