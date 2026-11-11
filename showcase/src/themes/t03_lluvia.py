"""03 · Lluvia en la ventana: sus iniciales escritas con el dedo en el vaho del vidrio.

Personalizable: iniciales y la frase.
Sorpresa (relación a distancia): en el vaho aparece la cuenta regresiva para volver a verse.
"""
import math
import numpy as np
from common import (W, H, T, TAU, blur, gauss_sprite, heart_mask, hexc, sm, text_mask, vgrad, vignette,
                    window, finish)

TITLE = "Lluvia en la ventana"
CAPTION = "Sus iniciales escritas en el vaho del vidrio"
SPECIAL = "¿A distancia? Cuenta los días para volver a verse"

BOKEH = ["#ffb347", "#ff7e5f", "#ffd27f", "#ffcf9e", "#5fd3ff", "#8a7dff", "#ff8fc7", "#ffe9b0"]


class Theme:
    def __init__(self, special=False):
        rng = np.random.default_rng(3)
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)

        # ciudad de noche desenfocada
        clear = vgrad([(0, "#070a16"), (0.45, "#111830"), (0.75, "#1d1a2e"), (1, "#100c18")])
        lights = np.zeros((H, W, 3), np.float32)
        for i in range(110):
            r = rng.uniform(22, 95)
            cy = rng.uniform(950, 1850) if i < 35 else rng.uniform(0.25, 1.0) ** 0.7 * H
            cx = rng.uniform(-50, W + 50)
            c = hexc(rng.choice(BOKEH)) * rng.uniform(0.35, 0.95)
            y0, y1 = int(max(cy - r - 3, 0)), int(min(cy + r + 3, H))
            x0, x1 = int(max(cx - r - 3, 0)), int(min(cx + r + 3, W))
            if y1 <= y0 or x1 <= x0:
                continue
            d = np.hypot(y[y0:y1, x0:x1] - cy, x[y0:y1, x0:x1] - cx)
            disk = np.clip(r - d, 0, 1.5) / 1.5 * (0.75 + 0.25 * (d / r) ** 3)
            lights[y0:y1, x0:x1] += disk[..., None] * c
        clear += blur(lights, 2.0) * 1.1
        clear *= vignette(0.45)
        self.clear = clear
        fogc = hexc("#9fb0c8")
        self.fog = blur(clear, 30) * 0.5 + fogc * 0.24 + blur(rng.random((H, W)).astype(np.float32), 3)[..., None] * 0.04

        # gotitas fijas en el vidrio (pegadas en las dos versiones)
        drops_a = np.zeros((H, W), np.float32)
        drops_hi = np.zeros((H, W), np.float32)
        for _ in range(1000):
            r = rng.uniform(1.5, 5.5) if rng.random() < 0.92 else rng.uniform(6, 11)
            cy, cx = rng.uniform(0, H), rng.uniform(0, W)
            y0, y1 = int(max(cy - r - 2, 0)), int(min(cy + r + 2, H))
            x0, x1 = int(max(cx - r - 2, 0)), int(min(cx + r + 2, W))
            if y1 <= y0 or x1 <= x0:
                continue
            yy, xx = y[y0:y1, x0:x1] - cy, x[y0:y1, x0:x1] - cx
            d = np.hypot(yy, xx * 1.08)
            drops_a[y0:y1, x0:x1] = np.maximum(drops_a[y0:y1, x0:x1], np.clip(r - d, 0, 1))
            hi = np.exp(-((yy + r * 0.4) ** 2 + (xx + r * 0.35) ** 2) / (2 * (r * 0.22) ** 2))
            drops_hi[y0:y1, x0:x1] += hi
        self.drops_a = drops_a[..., None]
        self.drops_hi = drops_hi[..., None] * 0.5
        self.lens = blur(clear, 6) * 0.8 + self.fog * 0.55   # lo que se ve "a través" de una gota

        # lo escrito con el dedo
        if special:
            words = text_mask("12 días", "caveat", 250, cy=1150, wght=700, stroke=4)
            line = text_mask("para volver a verte", "caveat", 110, cy=1720, wght=700, stroke=0)
        else:
            words = text_mask("S + E", "caveat", 300, cy=1150, wght=700, stroke=5)
            line = text_mask("llueve, pero contigo no importa", "caveat", 100, cy=1720, wght=700, stroke=0)
        heart = heart_mask(250, cx=540, cy=1450, w=W, h=H, outline=26)
        self.words = blur(words, 2.5)
        self.line = blur(line, 1.0)
        self.heart = blur(heart, 2.5)
        hy, hx = 1450, 540
        ang = (np.arctan2(x - hx, -(y - hy - 30)) / TAU) % 1   # 0 arriba, vuelta horaria
        self.heart_ang = ang.astype(np.float32)
        self.xs = x[0] / W

        # gotas que escurren
        self.runners = []
        for i in range(10):
            self.runners.append(dict(x=rng.uniform(40, W - 40), y0=rng.uniform(0, 1), k=int(rng.integers(1, 3)),
                                     ph=rng.uniform(0, TAU), r=rng.uniform(8, 13), trail=rng.uniform(300, 700)))
        self.bigdrop = {}

    def drop_sprite(self, r):
        r = int(r)
        if r not in self.bigdrop:
            yy, xx = np.mgrid[-r - 2:r * 1.4 + 3, -r - 2:r + 3].astype(np.float32)
            d = np.hypot(xx, np.where(yy > 0, yy / 1.4, yy))
            a = np.clip(r - d, 0, 1)
            hi = np.exp(-((yy + r * 0.4) ** 2 + (xx + r * 0.35) ** 2) / (2 * (r * 0.25) ** 2))
            self.bigdrop[r] = (a, hi)
        return self.bigdrop[r]

    def frame(self, t):
        # cuánto se ha limpiado el vaho en cada pixel
        fade = 1 - sm((t - 8.2) / 1.6)
        sweep = sm((self.xs * 1.0 - (t - 0.3) / 1.8 + 0.1) * -12 + 0.5)       # de izquierda a derecha
        m = self.words * sweep[None, :]
        hprog = (t - 2.0) / 1.1
        m = np.maximum(m, self.heart * sm((hprog - self.heart_ang) * 20 + 0.5))
        sweep2 = sm((self.xs - (t - 3.0) / 1.8 + 0.1) * -12 + 0.5)
        m = np.maximum(m, self.line * sweep2[None, :])
        m *= fade

        # escurrimientos: dejan un camino limpio
        heads = []
        for d in self.runners:
            u = (d["y0"] + d["k"] * t / T) % 1
            hy = -200 + u * (H + 400)
            ys = np.arange(int(max(hy - d["trail"], 0)), int(min(hy, H)))
            if len(ys):
                xs = (d["x"] + 5 * np.sin(ys / 47 + d["ph"])).astype(int)
                w = np.clip(1 - (hy - ys) / d["trail"], 0, 1) ** 1.5
                for off in range(-3, 4):
                    m[ys, xs + off] = np.maximum(m[ys, xs + off], w * (1 - abs(off) / 4.5))
            heads.append((hy, d["x"] + 5 * math.sin(hy / 47 + d["ph"]), d["r"]))

        m = m[..., None]
        F = self.fog * (1 - m) + self.clear * m
        F = F * (1 - self.drops_a) + self.lens * self.drops_a + self.drops_hi
        for hy, hx, r in heads:
            a, hi = self.drop_sprite(r)
            h, w = a.shape
            y0, x0 = int(hy) - int(r) - 2, int(hx) - w // 2
            sy0, sy1 = max(-y0, 0), min(h, H - y0)
            if sy1 <= sy0:
                continue
            reg = F[y0 + sy0:y0 + sy1, x0:x0 + w]
            aa = a[sy0:sy1, :, None]
            reg[:] = reg * (1 - aa) + self.lens[y0 + sy0:y0 + sy1, x0:x0 + w] * 1.1 * aa + hi[sy0:sy1, :, None] * 0.7
        return finish(F)
