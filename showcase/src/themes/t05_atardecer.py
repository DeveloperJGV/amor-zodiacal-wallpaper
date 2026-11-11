"""05 · Atardecer: el sol se mete en el mar y sus nombres están escritos en la arena.

Personalizable: nombres (o cualquier frase escrita en la arena).
Sorpresa (la pedida): en la arena dice "¿Te casas conmigo?".
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from common import (W, H, T, TAU, Patch, add, blur, hexc, over, sm, text_mask, vgrad, vignette, finish)

TITLE = "Atardecer"
CAPTION = "Sus nombres escritos en la arena"
SPECIAL = "Hasta para pedir matrimonio"

if W > H:   # escritorio: horizonte más alto, arena angosta y los nombres en una línea
    HOR, SHORE, REACH = 520, 790, 95
else:
    HOR, SHORE, REACH = 1050, 1560, 175


def bird_frames():
    out = []
    for k in range(8):
        f = math.sin(TAU * k / 8)
        img = Image.new("L", (60, 40), 0)
        d = ImageDraw.Draw(img)
        wing = 12 * f
        d.line([(4, 20 - wing), (18, 16 - wing * 0.3), (30, 22), (42, 16 - wing * 0.3), (56, 20 - wing)],
               fill=255, width=3, joint="curve")
        out.append(np.asarray(img, np.float32) / 255)
    return out


class Theme:
    def __init__(self, special=False):
        rng = np.random.default_rng(5)
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        hy, sh = HOR / H, SHORE / H
        F = vgrad([(0, "#1d1440"), (hy * 0.356, "#4a2466"), (hy * 0.669, "#a23d6e"), (hy * 0.891, "#f07a5e"),
                   (hy, "#ffd49a"), (hy + 0.0005, "#c96a72"), (hy + (sh - hy) * 0.373, "#6c3a6c"), (sh, "#3a2d5c"),
                   (sh + 0.0005, "#e9b48f"), (sh + (1 - sh) * 0.55, "#d79c78"), (1, "#b7795f")])
        sky = (y < HOR)[..., None]
        sun_d = np.hypot(x - W / 2, y - HOR + 10)
        glow = np.exp(-sun_d / 260) * 0.55 + np.exp(-sun_d / 90) * 0.4
        F += glow[..., None] * hexc("#ffb36b") * sky
        F += (np.clip(115 - sun_d, 0, 1.5) / 1.5)[..., None] * hexc("#fff3d0") * sky

        # nubes alargadas, iluminadas desde abajo
        clouds = np.zeros((H, W), np.float32)
        for _ in range(int(16 * W / 1080)):
            cy, cx = rng.uniform(HOR * 0.362, HOR * 0.914), rng.uniform(-100, W + 100)
            ry, rx = rng.uniform(10, 26), rng.uniform(120, 340)
            clouds += np.exp(-(((y - cy) / ry) ** 2 + ((x - cx) / rx) ** 2)) * rng.uniform(0.4, 0.9)
        clouds = np.clip(clouds, 0, 1)
        lit = ((y - HOR / 3) / (HOR * 0.62)).clip(0, 1)[..., None]
        ccol = hexc("#8a4a86") * (1 - lit) + hexc("#ffb48a") * lit
        F = F * (1 - 0.55 * clouds[..., None]) + clouds[..., None] * ccol * 0.6

        # arena con granito y el reflejo del cielo sobre el agua
        sand = (y >= SHORE)[..., None]
        grain = blur(rng.random((H, W)).astype(np.float32), 0.7) - 0.5
        F += grain[..., None] * 0.07 * sand
        F *= vignette(0.35)
        self.base = F

        # nombres marcados en la arena: surco oscuro y borde iluminado
        if W > H:
            line = "¿Te casas conmigo?" if special else "Camila & Rodrigo"
            m = text_mask(line, "dancing", 120, cy=SHORE + 160, wght=700)
        elif special:
            m = np.maximum(text_mask("¿Te casas", "dancing", 150, cy=1790, wght=700),
                           text_mask("conmigo?", "dancing", 150, cy=1960, wght=700))
        else:
            m = np.maximum(text_mask("Camila", "dancing", 170, cy=1790, wght=700),
                           text_mask("& Rodrigo", "dancing", 150, cy=1975, wght=700))
        g = blur(m, 2.5)
        self.groove = Patch(g)
        rim = np.clip(np.roll(g, 4, 0) - g, 0, 1)
        self.rim = Patch(blur(rim, 1.5))

        # agua: brillos del sol
        sea_y = y[HOR:SHORE] - HOR
        sea_x = x[HOR:SHORE]
        self.depth = SHORE - HOR
        self.sea_env = np.exp(-((sea_x - W / 2) / (50 + 0.55 * sea_y)) ** 2) * (1 - sea_y / (self.depth * 1.37))
        self.sea_y, self.sea_x = sea_y, sea_x
        self.shore_x = np.arange(W, dtype=np.float32)
        self.ph = rng.uniform(0, TAU, 4)
        self.birds = bird_frames()
        self.yy = np.arange(SHORE - 20, SHORE + 260, dtype=np.float32)[:, None]

    def frame(self, t):
        F = self.base.copy()
        a = TAU * t / T

        # destellos en el agua
        sy, sx = self.sea_y, self.sea_x
        g1 = 0.5 + 0.5 * np.sin(sx * 0.045 + 4 * np.sin(sy * 0.05 + a * 2) + a * 3)
        g2 = 0.5 + 0.5 * np.sin(sy * (0.9 - sy / 1400) - a * 6 + sx * 0.004)
        glint = (g1 * g2) ** 5 * self.sea_env
        F[HOR:SHORE] += glint[..., None] * hexc("#ffe2a8") * 1.3
        waves = (0.5 + 0.5 * np.sin(sy * (0.12 + sy / 4000) - a * 4)) ** 8 * (sy / self.depth)
        F[HOR:SHORE] += waves[..., None] * hexc("#c18aa8") * 0.12

        # nombres en la arena
        over(F, self.groove, hexc("#8f5a46"), 0.55)
        add(F, self.rim, hexc("#ffe0bf"), 0.25)

        # ola: sube y baja dos veces por ciclo
        u = (t % 5.0) / 5.0
        reach = REACH * math.sin(math.pi * min(u / 0.75, 1)) ** 1.2 if u < 0.75 else 0
        xs = self.shore_x
        front = SHORE + reach + 14 * np.sin(xs / 75 + self.ph[0] + a) + 7 * np.sin(xs / 23 + self.ph[1])
        front = np.minimum(front, SHORE + reach + 20)
        yy = self.yy
        band = F[SHORE - 20:SHORE + 260]
        water = sm((front[None, :] - yy) / 6) * (yy > SHORE - 20)
        peak = SHORE + REACH
        wet = sm((peak - yy) / 25) * float(sm(u / 0.35) * (1 - sm((u - 0.45) / 0.5))) * 0.35
        band *= 1 - (wet * 0.35 * (yy > SHORE))[..., None]
        depth = np.clip((front[None, :] - yy) / 90, 0.25, 1) * water
        band[:] = band * (1 - depth[..., None] * 0.45) + depth[..., None] * hexc("#9d6f96") * 0.45
        foam = np.exp(-((yy - front[None, :] + 4) / 5) ** 2) * (0.6 + 0.4 * np.sin(xs / 9 + a * 5) ** 2)
        band += foam[..., None] * hexc("#fff1e6") * 0.55 * (reach > 3)
        band += np.exp(-((yy - SHORE) / 3) ** 2)[..., None] * hexc("#fff1e6") * 0.25   # rompiente

        # dos gaviotas cruzando
        for i, (y0, sp, ph) in enumerate(((HOR * 0.533, 1, 0.0), (HOR * 0.61, 1, 0.45))):
            px = -80 + ((t / T * sp + ph) % 1) * (W + 160)
            py = y0 + 18 * math.sin(a * 2 + i)
            fr = self.birds[int((t * 6 + i * 3) % 8)]
            p = Patch(np.zeros((1, 1)))
            p.y0, p.x0 = int(py), int(px) - 30
            if 0 <= p.x0 < W - 60:
                p.a = fr
                over(F, p, hexc("#2a1838"), 0.85)
        return finish(F)
