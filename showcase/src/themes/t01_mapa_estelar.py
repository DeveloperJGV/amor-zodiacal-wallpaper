"""01 · Mapa estelar: el cielo de la noche en que se conocieron.

Personalizable: nombres, fecha, ciudad y coordenadas.
Sorpresa (aniversario): las estrellas se unen en un corazón y dice cuántos años llevan.
"""
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw
from common import (W, H, T, TAU, Patch, add, blit, blur, flare_sprite, gauss_sprite, heart_points, hexc,
                    sm, text_mask, vgrad, vignette, window, finish)

TITLE = "Mapa estelar"
CAPTION = "El cielo exacto de la noche en que se conocieron"
SPECIAL = "En su aniversario, las estrellas forman un corazón"

CX, CY, R = 540, 1180, 420
GOLD = hexc("#e6c27a")
CREAM = hexc("#f6ead0")


class Theme:
    def __init__(self, special=False):
        self.special = special
        rng = np.random.default_rng(1)
        F = vgrad([(0, "#03050f"), (0.45, "#0a1433"), (0.8, "#141a44"), (1, "#0c0a24")])
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot(x - CX, y - CY)
        inside = (d < R).astype(np.float32)

        # vía láctea: banda diagonal con grumos, sólo dentro del círculo
        band = np.exp(-(((x - CX) * 0.55 + (y - CY) * 0.83) / 120) ** 2)
        clumps = blur(rng.random((H // 8, W // 8)).astype(np.float32), 2)
        clumps = cv2.resize(clumps, (W, H), interpolation=cv2.INTER_CUBIC)
        mw = blur(band * (0.4 + clumps) * inside, 6)
        F += mw[..., None] * hexc("#7b6cc4") * 0.16
        F += inside[..., None] * hexc("#1b2a66") * 0.18  # el cielo del mapa un poco más claro
        F *= vignette(0.55)

        # aros, marcas de grados y puntos cardinales
        img = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(img)
        dr.ellipse((CX - R, CY - R, CX + R, CY + R), outline=255, width=3)
        dr.ellipse((CX - R - 22, CY - R - 22, CX + R + 22, CY + R + 22), outline=150, width=1)
        for k in range(180):
            a = TAU * k / 180
            l = 16 if k % 15 == 0 else 7
            r0, r1 = R + 4, R + 4 + l
            dr.line((CX + r0 * math.cos(a), CY + r0 * math.sin(a), CX + r1 * math.cos(a), CY + r1 * math.sin(a)),
                    fill=200 if l > 10 else 110, width=2 if l > 10 else 1)
        ring = np.asarray(img, np.float32) / 255
        for lab, ang in (("N", -90), ("E", 0), ("S", 90), ("O", 180)):
            a = math.radians(ang)
            ring = np.maximum(ring, text_mask(lab, "mont", 26, CX + (R + 52) * math.cos(a),
                                              CY + (R + 52) * math.sin(a), wght=500) * 0.8)
        add(F, Patch(ring), GOLD, 0.75)

        # estrellas: dentro del mapa densas, afuera pocas y tenues
        n_in = 430
        rr = R * np.sqrt(rng.random(n_in)) * 0.97
        aa = rng.random(n_in) * TAU
        sy, sx = CY + rr * np.sin(aa), CX + rr * np.cos(aa)
        mag = rng.pareto(2.2, n_in) + 0.25
        out_y, out_x = rng.random(260) * H, rng.random(260) * W
        keep = np.hypot(out_x - CX, out_y - CY) > R + 70
        self.stars = []
        for i in range(n_in):
            m = min(mag[i], 4)
            col = hexc(rng.choice(["#ffffff", "#dfe8ff", "#fff1d6", "#ffe0c2"]))
            self.stars.append((sy[i], sx[i], 0.6 + 0.45 * m, 0.35 + 0.4 * m, col,
                               int(rng.integers(1, 4)), rng.random() * TAU, m > 2.2))
        for yy, xx in zip(out_y[keep], out_x[keep]):
            self.stars.append((yy, xx, 0.7, 0.18 + 0.2 * rng.random(), CREAM, int(rng.integers(1, 3)),
                               rng.random() * TAU, False))

        # constelaciones: cadenas entre estrellas brillantes vecinas
        bright = [i for i in range(n_in) if mag[i] > 1.0]
        lines = Image.new("L", (W, H), 0)
        dl = ImageDraw.Draw(lines)
        used = set()
        for seed in rng.choice(bright, 7, replace=False):
            cur, chain = seed, [seed]
            for _ in range(int(rng.integers(3, 6))):
                cand = [j for j in bright if j not in used and j not in chain]
                dd = [math.hypot(sy[j] - sy[cur], sx[j] - sx[cur]) for j in cand]
                if not cand or min(dd) > 150:
                    break
                cur = cand[int(np.argmin(dd))]
                chain.append(cur)
            used.update(chain)
            dl.line([(sx[j], sy[j]) for j in chain], fill=255, width=2)
        self.lines = Patch(np.asarray(lines, np.float32) / 255)

        # textos
        if special:
            texts = [("VALERIA & ANDRÉS", "mont", 50, 1730, 500, 10, CREAM, 0.95),
                     ("Feliz aniversario", "playfair-i", 52, 1815, 400, 0, GOLD, 1.0),
                     ("3 AÑOS BAJO EL MISMO CIELO", "mont", 28, 1895, 400, 8, CREAM, 0.8)]
        else:
            texts = [("VALERIA & ANDRÉS", "mont", 50, 1730, 500, 10, CREAM, 0.95),
                     ("La noche que nos conocimos", "playfair-i", 46, 1810, 400, 0, GOLD, 1.0),
                     ("14 · 02 · 2021", "mont", 30, 1885, 400, 9, CREAM, 0.85)]
        texts.append(("GUADALAJARA, MÉXICO  ·  20.66° N  103.35° O", "mont", 22, 1940, 400, 4, CREAM, 0.5))
        for s, f, size, ty, wg, tr, col, a in texts:
            add(F, Patch(text_mask(s, f, size, cy=ty, wght=wg, tracking=tr)), col, a)
        self.base = F

        # sorpresa: corazón de estrellas en el centro del mapa
        hp = heart_points(16) * 175 + [CX, CY - 15]
        self.heart = hp
        segs = Image.new("L", (W, H), 0)
        self.heart_segs = []
        for i in range(len(hp)):
            a, b = hp[i], hp[(i + 1) % len(hp)]
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).line((a[0], a[1], b[0], b[1]), fill=255, width=3)
            self.heart_segs.append(Patch(np.asarray(m, np.float32) / 255))
        self.heart_glow = Patch(blur(sum(p_full(s) for s in self.heart_segs), 10))

    def frame(self, t):
        F = self.base.copy()
        add(F, self.lines, GOLD, 0.22 + 0.12 * math.sin(TAU * t / T))
        for y, x, sig, amp, col, k, ph, big in self.stars:
            a = amp * (0.72 + 0.28 * math.sin(TAU * k * t / T + ph))
            blit(F, gauss_sprite(round(sig * 2) / 2), y, x, col, a)
            if big:
                blit(F, flare_sprite(26), y, x, col, a * 0.35)

        # estrella fugaz
        u = (t - 6.2) / 0.9
        if 0 <= u <= 1:
            hy, hx = CY - 300 + 380 * u, CX + 330 - 420 * u
            for j in range(140):
                f = j / 140
                blit(F, gauss_sprite(round(3 + 2 * (1 - f)) / 2), hy - 1.35 * j, hx + 1.5 * j, CREAM,
                     (1 - f) ** 2 * math.sin(math.pi * u) * 0.45)

        if self.special:
            n = len(self.heart_segs)
            for i, p in enumerate(self.heart_segs):
                a = sm((t - 0.8 - i * 0.16) / 0.25) * window(t, 0, 9.4, 0.6)
                add(F, p, GOLD, 0.7 * a)
            g = sm((t - 0.8 - n * 0.16) / 0.6) * window(t, 0, 9.4, 0.6)
            add(F, self.heart_glow, hexc("#ff8fb0"), 0.25 * g * (0.8 + 0.2 * math.sin(TAU * 3 * t / T)))
            for i, (x, y) in enumerate(self.heart):
                a = sm((t - 0.6 - i * 0.16) / 0.3) * window(t, 0, 9.4, 0.6)
                blit(F, flare_sprite(30), y, x, hexc("#fff3e6"), 0.9 * a)
        return finish(F)


def p_full(p):
    m = np.zeros((H, W), np.float32)
    h, w = p.a.shape
    m[p.y0:p.y0 + h, p.x0:p.x0 + w] = p.a
    return m
