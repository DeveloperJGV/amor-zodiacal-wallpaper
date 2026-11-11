"""10 · Nuestra canción: un reproductor con un vinilo girando y la letra que les gusta.

Personalizable: nombre de la canción, la frase de la letra, sus iniciales en el disco.
Sorpresa (14 de febrero): la letra cambia y suben corazones.
"""
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw
from common import (W, H, T, TAU, Patch, add, blit, blur, heart_mask, hexc, over, sm, text_mask, finish)

TITLE = "Nuestra canción"
CAPTION = "Su canción, sonando para siempre en su pantalla"
SPECIAL = "El 14 de febrero, la letra cambia"

CX, CY, R = 540, 1130, 300
LR = 105                     # radio de la etiqueta del disco
BAR_Y, BAR_X0, BAR_X1 = 1650, 150, 930
SONG_LEN, START = 225, 84    # 3:45, empieza en 1:24
LYRICS = ["y en mis días grises", "tú eres mi color", "quédate, que contigo", "todo suena mejor"]
LYRICS_S = ["feliz 14 de febrero", "mi canción favorita", "siempre vas a ser", "tú"]


def mmss(s):
    return f"{int(s) // 60}:{int(s) % 60:02d}"


class Theme:
    def __init__(self, special=False):
        self.special = special
        rng = np.random.default_rng(10)
        self.blobs = [(hexc(c), rng.uniform(0.2, 0.8), rng.uniform(0.15, 0.85), rng.uniform(0.25, 0.45),
                       int(k), rng.uniform(0, TAU))
                      for c, k in (("#ff6a4d", 1), ("#ffb35c", 1), ("#9b4dff", 2), ("#ff3f8e", 1), ("#3d2bff", 1))]
        self.ly, self.lx = np.mgrid[0:117, 0:54].astype(np.float32)
        self.ly /= 117
        self.lx /= 54

        # disco: surcos y brillo fijos (giran sin que se note), etiqueta que sí gira
        y, x = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        d = np.hypot(x, y)
        ang = np.arctan2(y, x)
        disk = np.clip(R - d, 0, 1.5) / 1.5
        groove = 0.06 + 0.035 * (np.sin(d * 1.9) ** 2) * (d > LR + 15) + 0.02 * (np.sin(d * 0.21) > 0.9)
        sheen = (np.cos(2 * (ang - 0.7)) ** 16) * 0.22 * (d > LR + 8) * (d / R)
        vinyl = np.zeros((2 * R + 1, 2 * R + 1, 4), np.float32)
        vinyl[..., :3] = (groove + sheen)[..., None] * hexc("#ffffff") + hexc("#0b0b10") * 0.6
        vinyl[..., 3] = disk
        self.vinyl = vinyl

        lab = Image.new("RGBA", (2 * LR, 2 * LR), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lab)
        c1, c2 = ((255, 95, 150), (255, 160, 110)) if not special else ((255, 70, 120), (255, 120, 170))
        for i in range(LR, 0, -1):
            f = i / LR
            col = tuple(int(c1[k] * f + c2[k] * (1 - f)) for k in range(3)) + (255,)
            dl.ellipse((LR - i, LR - i, LR + i, LR + i), fill=col)
        lab = np.asarray(lab, np.float32) / 255
        txt = text_mask("R & P", "vibes", 64, cx=LR, cy=LR - 22, w=2 * LR, h=2 * LR)
        txt2 = text_mask("LADO A · 2016", "mont", 13, cx=LR, cy=LR + 42, w=2 * LR, h=2 * LR, wght=600, tracking=2)
        lab[..., :3] = lab[..., :3] * (1 - txt[..., None]) + txt[..., None] * hexc("#fff6ee")
        lab[..., :3] = lab[..., :3] * (1 - txt2[..., None] * 0.8) + txt2[..., None] * 0.8 * hexc("#5a1230")
        yy, xx = np.mgrid[-LR:LR, -LR:LR]
        hole = np.hypot(xx, yy) < 7
        lab[hole, 3] = 0
        self.label = lab

        # textos y controles fijos
        self.static = []
        self.static.append((Patch(text_mask("Nuestra canción", "mont", 56, left=150, cy=1520, wght=700)), "#ffffff", 1.0))
        self.static.append((Patch(text_mask("Regina & Pablo", "mont", 36, left=150, cy=1585, wght=400)), "#ffffff", 0.7))
        img = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(img)
        cy = 1790
        d.ellipse((540 - 62, cy - 62, 540 + 62, cy + 62), fill=255)
        d.polygon([(340, cy), (390, cy - 30), (390, cy + 30)], fill=255)
        d.rectangle((326, cy - 30, 334, cy + 30), fill=255)
        d.polygon([(740, cy), (690, cy - 30), (690, cy + 30)], fill=255)
        d.rectangle((746, cy - 30, 754, cy + 30), fill=255)
        ctrl = np.asarray(img, np.float32) / 255
        self.static.append((Patch(ctrl), "#ffffff", 0.95))
        pause = Image.new("L", (W, H), 0)
        ImageDraw.Draw(pause).rectangle((520, cy - 26, 532, cy + 26), fill=255)
        ImageDraw.Draw(pause).rectangle((548, cy - 26, 560, cy + 26), fill=255)
        self.pause = Patch(np.asarray(pause, np.float32) / 255)
        self.like = Patch(heart_mask(52, cx=905, cy=1550, w=W, h=H))
        self.lyrics = [Patch(text_mask(s, "playfair-i", 60, cy=1960, wght=400))
                       for s in (LYRICS_S if special else LYRICS)]
        self.times = {}
        self.bars_ph = rng.uniform(0, TAU, 96)
        self.bars_k = rng.integers(2, 7, 96)
        self.floaters = [(rng.uniform(80, W - 80), rng.random(), int(rng.integers(1, 3)), int(rng.integers(20, 44)) // 2 * 2,
                          rng.uniform(0, TAU)) for _ in range(18)]
        self.hearts = {}

    def time_patch(self, s, right):
        key = (s, right)
        if key not in self.times:
            self.times[key] = Patch(text_mask(s, "mont", 26, cx=BAR_X1 - 30 if right else BAR_X0 + 30, cy=BAR_Y + 42,
                                              wght=500))
        return self.times[key]

    def frame(self, t):
        a = TAU * t / T
        # fondo: manchas de color que se mueven despacio
        small = np.zeros((117, 54, 3), np.float32) + hexc("#140a26")
        for col, by, bx, r, k, ph in self.blobs:
            cy = by + 0.08 * math.sin(k * a + ph)
            cx = bx + 0.12 * math.cos(k * a + ph * 1.3)
            small += np.exp(-((self.ly - cy) ** 2 * 4.6 + (self.lx - cx) ** 2) / (2 * r * r))[..., None] * col * 0.85
        F = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC) * 0.55

        # barras del ecualizador alrededor del disco
        bars = np.zeros((H, W), np.uint8)
        for i in range(96):
            ang = TAU * i / 96
            h = 18 + 46 * (0.5 + 0.5 * math.sin(self.bars_k[i] * a + self.bars_ph[i])) ** 2
            r0 = R + 26
            p0 = (int(CX + r0 * math.cos(ang)), int(CY + r0 * math.sin(ang)))
            p1 = (int(CX + (r0 + h) * math.cos(ang)), int(CY + (r0 + h) * math.sin(ang)))
            cv2.line(bars, p0, p1, 255, 7, cv2.LINE_AA)
        bars = bars.astype(np.float32) / 255
        F += bars[..., None] * hexc("#ffd1e0") * 0.55
        F += blur(bars, 14)[..., None] * hexc("#ff6aa2") * 0.5

        # disco
        y0, x0 = CY - R, CX - R
        sh = blur(np.pad(self.vinyl[..., 3], 30), 18)
        F[y0 - 30 + 20:y0 + 2 * R + 1 + 30 + 20, x0 - 30:x0 + 2 * R + 1 + 30] *= 1 - sh[..., None] * 0.5
        r = F[y0:y0 + 2 * R + 1, x0:x0 + 2 * R + 1]
        al = self.vinyl[..., 3:]
        r[:] = r * (1 - al) + self.vinyl[..., :3] * al
        rot = -360 * 5 * t / T                       # 5 vueltas por ciclo (30 rpm)
        M = cv2.getRotationMatrix2D((LR, LR), rot, 1.0)
        lab = cv2.warpAffine(self.label, M, (2 * LR, 2 * LR), flags=cv2.INTER_LINEAR)
        r = F[CY - LR:CY + LR, CX - LR:CX + LR]
        al = lab[..., 3:]
        r[:] = r * (1 - al) + lab[..., :3] * al

        for p, c, amp in self.static:
            add(F, p, hexc(c), amp)
        over(F, self.pause, hexc("#2a1238"), 1.0)
        add(F, self.like, hexc("#ff3f8e"), 1.0)

        # barra de progreso
        el = START + t
        frac = el / SONG_LEN
        xm = int(BAR_X0 + (BAR_X1 - BAR_X0) * frac)
        F[BAR_Y - 3:BAR_Y + 3, BAR_X0:BAR_X1] = F[BAR_Y - 3:BAR_Y + 3, BAR_X0:BAR_X1] * 0.6 + 0.4 * 0.35
        F[BAR_Y - 3:BAR_Y + 3, BAR_X0:xm] = hexc("#ffffff")
        yy, xx = np.mgrid[-12:13, -12:13]
        knob = np.clip(12 - np.hypot(yy, xx), 0, 1).astype(np.float32)
        blit(F, knob, BAR_Y, xm, hexc("#ffffff"), 1.0)
        add(F, self.time_patch(mmss(el), False), hexc("#ffffff"), 0.7)
        add(F, self.time_patch("-" + mmss(SONG_LEN - el), True), hexc("#ffffff"), 0.7)

        # la letra va cambiando
        n = len(self.lyrics)
        seg = T / n
        for i, p in enumerate(self.lyrics):
            u = (t - i * seg) % T
            add(F, p, hexc("#fff2f6"), 0.95 * sm(u / 0.5) * sm((seg - u) / 0.5) if u < seg else 0)

        if self.special:
            for x0f, y0f, k, size, ph in self.floaters:
                u = (y0f + k * t / T) % 1
                if size not in self.hearts:
                    self.hearts[size] = heart_mask(size)
                blit(F, self.hearts[size], H + 40 - u * (H + 80), x0f + 30 * math.sin(TAU * 2 * u + ph),
                     hexc("#ff4f9a"), 0.55 * sm(u / 0.1) * sm((1 - u) / 0.3))
        return finish(F)
