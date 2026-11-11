"""07 · Sakura: ramas de cerezo en flor y pétalos que caen sobre sus nombres.

Personalizable: nombres, año y colores.
Sorpresa (cumpleaños): lluvia de pétalos y "Feliz cumpleaños".
"""
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw
from common import (W, H, T, TAU, Patch, add, over, over_img, blur, hexc, text_mask, vgrad, finish)

TITLE = "Sakura"
CAPTION = "Pétalos de cerezo sobre sus nombres"
SPECIAL = "En su cumpleaños, lluvia de pétalos"

PETALS = ["#ffb7cc", "#ff9fbd", "#ffd3e0", "#ffc6d6", "#f78fb0"]
S = 2   # sobremuestreo para que las ramas y flores queden suaves


def branch(d, x, y, ang, length, width, depth, rng, tips, base=None):
    base = ang if base is None else base
    if depth == 0 or length < 10:
        tips.append((x, y))
        return
    n = 6
    px, py = x, y
    for i in range(n):          # rama un poco curva
        ang += rng.uniform(-0.12, 0.12)
        nx, ny = px + length / n * math.cos(ang), py - length / n * math.sin(ang)
        wdt = width * (1 - 0.35 * i / n)
        d.line((px * S, py * S, nx * S, ny * S), fill=(74, 44, 42, 255), width=max(int(wdt * S), 2))
        d.ellipse(((nx - wdt / 2) * S, (ny - wdt / 2) * S, (nx + wdt / 2) * S, (ny + wdt / 2) * S), fill=(74, 44, 42, 255))
        px, py = nx, ny
        if depth < 5 and rng.random() < 0.3:
            tips.append((px, py))
    for k in range(2 if rng.random() < 0.75 else 3):
        a = ang + rng.uniform(-0.8, 0.8)
        a = base + (a - base) * 0.55          # que se abra de lado, no hacia arriba
        branch(d, px, py, a, length * rng.uniform(0.62, 0.8), width * 0.62, depth - 1, rng, tips, base)


def flower(d, x, y, r, rng):
    col = hexc(rng.choice(PETALS))
    c = tuple(int(v * 255) for v in col) + (255,)
    rot = rng.uniform(0, TAU)
    for k in range(5):
        a = rot + TAU * k / 5
        px, py = x + r * 0.55 * math.cos(a), y + r * 0.55 * math.sin(a)
        d.ellipse(((px - r * 0.52) * S, (py - r * 0.52) * S, (px + r * 0.52) * S, (py + r * 0.52) * S), fill=c)
    d.ellipse(((x - r * 0.22) * S, (y - r * 0.22) * S, (x + r * 0.22) * S, (y + r * 0.22) * S), fill=(214, 70, 112, 255))
    d.ellipse(((x - r * 0.1) * S, (y - r * 0.1) * S, (x + r * 0.1) * S, (y + r * 0.1) * S), fill=(255, 236, 170, 255))


def petal_sprites(size, blur_px=0):
    out = []
    for k in range(24):
        img = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c = size * 2
        d.ellipse((c - size * 0.8, c - size * 1.5, c + size * 0.8, c + size * 1.5), fill=(255, 175, 200, 255))
        d.ellipse((c - size * 0.35, c - size * 1.75, c + size * 0.35, c - size * 1.1), fill=(0, 0, 0, 0))  # muesca
        d.ellipse((c - size * 0.35, c - size * 0.6, c + size * 0.35, c + size * 1.1), fill=(255, 210, 222, 255))
        # giro en 3D aproximado: aplastar en x
        sq = abs(math.cos(TAU * k / 24)) * 0.8 + 0.2
        img = img.resize((max(int(size * 4 * sq), 2), size * 4), Image.LANCZOS)
        img = img.rotate(k * 37 % 360, expand=True, resample=Image.BICUBIC)
        a = np.asarray(img, np.float32) / 255
        if blur_px:
            # desenfocar premultiplicado; si no, el borde transparente (negro) ensucia el pétalo de gris
            pad = int(blur_px * 3)
            a = np.pad(a, ((pad, pad), (pad, pad), (0, 0)))
            alpha = blur(a[..., 3], blur_px)
            rgb = np.stack([blur(a[..., c] * a[..., 3], blur_px) for c in range(3)], -1)
            a = np.dstack([rgb / np.maximum(alpha, 1e-4)[..., None], alpha])
        out.append(a)
    return out


class Theme:
    def __init__(self, special=False):
        rng = np.random.default_rng(7)
        F = vgrad([(0, "#fff4f6"), (0.45, "#fbe1ea"), (1, "#f2bfd2")])
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        F += np.exp(-((x - 850) ** 2 + (y - 500) ** 2) / (2 * 420 ** 2))[..., None] * hexc("#fff3dc") * 0.25

        img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        tips = []
        branch(d, -40, 900, math.radians(8), 300, 34, 6, rng, tips)
        branch(d, W + 30, 1330, math.radians(170), 230, 26, 5, rng, tips)
        for tx, ty in tips:
            for _ in range(int(rng.integers(1, 3))):
                flower(d, tx + rng.normal(0, 16), ty + rng.normal(0, 16), rng.uniform(13, 22), rng)
        img = img.resize((W, H), Image.LANCZOS)
        a = np.asarray(img, np.float32) / 255
        shadow = blur(a[..., 3], 10)
        F *= 1 - shadow[..., None] * 0.12
        F = F * (1 - a[..., 3:]) + a[..., :3] * a[..., 3:]

        if special:
            add_lines = [("Feliz cumpleaños,", "vibes", 130, 1640), ("Ana", "vibes", 190, 1810)]
            sub = "QUE FLOREZCA TODO LO QUE QUIERES"
        else:
            add_lines = [("Ana & Luis", "vibes", 190, 1680)]
            sub = "FLORECIENDO JUNTOS DESDE 2019"
        for s, f, size, ty in add_lines:
            m = text_mask(s, f, size, cy=ty)
            over(F, Patch(blur(m, 3)), hexc("#ffffff"), 0.5)
            over(F, Patch(m), hexc("#9c3456"), 0.95)
        over(F, Patch(text_mask(sub, "mont", 26, cy=1950 if special else 1840, wght=500, tracking=8)),
             hexc("#b5577a"), 0.85)
        self.base = F

        n = 150 if special else 75
        sizes = [(9, 0), (12, 0), (16, 1.2), (24, 3.5)]
        self.sprites = [petal_sprites(s, b) for s, b in sizes]
        self.petals = []
        for i in range(n):
            si = 3 if rng.random() < 0.08 else int(rng.integers(0, 3))
            self.petals.append(dict(si=si, x0=rng.uniform(-40, W + 40), y0=rng.random(), k=int(rng.integers(1, 3)),
                                    sw=rng.uniform(30, 90), ph=rng.uniform(0, TAU), rot=int(rng.integers(0, 24)),
                                    spin=int(rng.integers(1, 4)) * (1 if rng.random() < 0.5 else -1),
                                    amp=rng.uniform(0.75, 1.0)))

    def frame(self, t):
        F = self.base.copy()
        for p in self.petals:
            u = (p["y0"] + p["k"] * t / T) % 1
            y = -120 + u * (H + 240)
            x = p["x0"] + p["sw"] * math.sin(TAU * 2 * u + p["ph"]) + 40 * u
            spr = self.sprites[p["si"]][int(p["rot"] + p["spin"] * 24 * t / T) % 24]
            h, w = spr.shape[:2]
            over_img(F, int(y) - h // 2, int(x) - w // 2, spr, p["amp"])
        return finish(F)
