"""06 · Luna: la luna pasa por todas sus fases; abajo, la fase exacta de su fecha.

Personalizable: nombres, fecha (con su fase lunar real) y la frase.
Sorpresa (aniversario): la luna se queda llena, con un halo rosado.
"""
import math
import numpy as np
from common import (W, H, T, TAU, Patch, add, blit, blur, gauss_sprite, glow_patch, hexc, sm, text_mask,
                    vgrad, vignette, finish)

TITLE = "Luna"
CAPTION = "La fase de la luna del día que se conocieron"
SPECIAL = "En su fecha, luna llena para ustedes"

CX, CY, R = 540, 1080, 270
ROW_Y, ROW_R = 1560, 32
DATE_IDX = 3          # 0 llena ... 4 nueva; la fase de "su" fecha
SILVER = hexc("#e9ecf5")
GOLD = hexc("#e7c98a")


def moon_albedo(r, rng):
    y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    alb = np.full(x.shape, 0.86, np.float32)
    for _ in range(16):           # mares
        cy, cx = rng.uniform(-0.7, 0.6) * r, rng.uniform(-0.7, 0.7) * r
        s = rng.uniform(0.08, 0.22) * r
        alb -= 0.13 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2 * rng.uniform(0.6, 1.4)) / (2 * s * s))
    for _ in range(70):           # cráteres
        cy, cx = rng.uniform(-1, 1, 2) * r
        s = rng.uniform(0.012, 0.06) * r
        d = np.hypot(x - cx, y - cy) / s
        alb += 0.035 * np.exp(-((d - 1) / 0.3) ** 2) - 0.045 * np.exp(-(d / 0.8) ** 2)
    alb += blur(rng.random(x.shape).astype(np.float32), 1.2) * 0.12 - 0.06
    return np.clip(alb, 0.3, 1)


def shade(alb, r, phi, earth=0.07):
    """phi = 0 llena, pi nueva. Devuelve brillo y máscara del disco."""
    n = alb.shape[0]
    y, x = np.mgrid[-r:r + 1, -r:r + 1][:, :n, :n].astype(np.float32) / r
    disk = np.clip((1 - np.hypot(x, y)) * r, 0, 1)
    nz = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    dot = x * math.sin(phi) + nz * math.cos(phi)
    lit = sm((dot + 0.04) / 0.14) * (0.55 + 0.45 * nz ** 0.4)
    return (lit + earth) * alb * disk, disk


class Theme:
    def __init__(self, special=False):
        self.special = special
        rng = np.random.default_rng(6)
        F = vgrad([(0, "#010208"), (0.4, "#070b1e"), (0.75, "#110c26"), (1, "#07050f")])
        F *= vignette(0.5)
        self.stars = [(rng.uniform(0, H), rng.uniform(0, W), rng.uniform(0.1, 0.6), rng.uniform(0, TAU),
                       int(rng.integers(1, 4))) for _ in range(320)]
        self.stars = [s for s in self.stars if math.hypot(s[0] - CY, s[1] - CX) > R + 30]
        self.alb = moon_albedo(R, rng)

        # fila de fases con la de su fecha marcada
        small = moon_albedo(ROW_R, np.random.default_rng(66))
        xs = np.linspace(150, 930, 8)
        for i, x0 in enumerate(xs):
            img, _ = shade(small, ROW_R, TAU * i / 8 if i else 0.0, earth=0.08)
            p = Patch(np.zeros((1, 1)))
            p.y0, p.x0, p.a = ROW_Y - ROW_R, int(x0) - ROW_R, img
            add(F, p, SILVER, 0.85)
        ring = np.zeros((H, W), np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot(xx - xs[DATE_IDX], yy - ROW_Y)
        ring = np.clip(1.5 - np.abs(d - ROW_R - 12), 0, 1)
        self.ring = Patch(ring)
        self.ring_glow = glow_patch(ring, 6)
        lab = text_mask("12 · 06 · 2022", "mont", 22, cx=xs[DATE_IDX], cy=ROW_Y + 68, wght=500, tracking=3)
        add(F, Patch(lab), GOLD, 0.9)

        if special:
            lines = [("Hoy hace 2 años,", 1760), ("bajo esta luna", 1845)]
        else:
            lines = [("Te amo hasta la luna", 1760), ("y de regreso", 1845)]
        for s, ty in lines:
            add(F, Patch(text_mask(s, "playfair-i", 64, cy=ty, wght=400)), SILVER, 0.95)
        add(F, Patch(text_mask("XIMENA & IVÁN", "mont", 30, cy=1950, wght=500, tracking=12)), GOLD, 0.85)
        self.base = F
        y, x = np.mgrid[-R * 3:R * 3 + 1, -R * 3:R * 3 + 1].astype(np.float32)
        self.halo = np.exp(-np.hypot(x, y) / (R * 0.55)) * (np.hypot(x, y) > R * 0.9)

    def phi(self, t):
        if self.special:
            return 0.0
        a = TAU * t / T
        return a - 0.9 * math.sin(a)          # se detiene más en la llena que en la nueva

    def frame(self, t):
        F = self.base.copy()
        a = TAU * t / T
        for y, x, amp, ph, k in self.stars:
            blit(F, gauss_sprite(1.0), y, x, SILVER, amp * (0.7 + 0.3 * math.sin(k * a + ph)))
        phi = self.phi(t)
        frac = 0.5 * (1 + math.cos(phi))
        hp = Patch(np.zeros((1, 1)))
        hp.y0, hp.x0, hp.a = CY - 3 * R, CX - 3 * R, self.halo
        add(F, hp, hexc("#ff9fc4") if self.special else hexc("#9fb3ff"), 0.12 + 0.4 * frac)
        img, disk = shade(self.alb, R, phi)
        reg = F[CY - R:CY + R + 1, CX - R:CX + R + 1]
        reg *= 1 - disk[..., None] * 0.9
        reg += img[..., None] * hexc("#f2efe6")
        pulse = 0.6 + 0.4 * math.sin(a * 2) ** 2
        add(F, self.ring, GOLD, 0.9)
        add(F, self.ring_glow, GOLD, 0.6 * pulse)
        if self.special:
            for i in range(14):
                ang = TAU * i / 14 + a * 0.5
                rr = R + 70 + 25 * math.sin(a * 3 + i)
                blit(F, gauss_sprite(2.0), CY + rr * math.sin(ang), CX + rr * math.cos(ang), hexc("#ffd1e3"),
                     0.6 * (0.5 + 0.5 * math.sin(a * 4 + i * 1.7)))
        return finish(F)
