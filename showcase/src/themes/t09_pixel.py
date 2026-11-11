"""09 · Jugador 2: pixel art de videojuego retro; la pareja como dos personajes.

Personalizable: nombres, colores de ropa/pelo, nivel = años juntos.
Sorpresa (aniversario): "¡SUBISTE DE NIVEL!" con confeti.
"""
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw
from common import W, H, T, TAU, hexc, finish, font

TITLE = "Jugador 2"
CAPTION = "Para parejas gamers: ustedes en pixel art"
SPECIAL = "En su aniversario, ¡suben de nivel!"

PX = 4                         # cada pixel del juego mide 4x4 en pantalla
LW, LH = W // PX, H // PX      # 270 x 585
GROUND = 470

PAL = {"K": "#1b1020", "S": "#f2c29b", "R": "#ff8fa3", "W": "#ffffff", "F": "#3a2418",
       "h": "#3a2418", "B": "#3b82f6", "b": "#2563eb", "P": "#2b2d6e",
       "H": "#8a3b1f", "G": "#ff5d8f", "g": "#e0457a", "Y": "#ffd166"}

BOY = ["...KKKKK...", "..KhhhhhK..", ".KhhhhhhhK.", ".KhhSSSShK.", ".KhSSKSSKK.", ".KSSSSSSRK.",
       "..KSSSSSK..", "..KbBBBbK..", ".KBBBBBBBK.", "KSKBBBBBKSK", "KSKBBBBBKSK", "..KPPPPPK..",
       "..KPPKPPK..", "..KPK.KPK..", "..KFK.KFK..", ".KFFK.KFFK."]
GIRL = ["...KKKKK...", "..KHHHHHK..", ".KHHHHHHHK.", "KHHSSSSHHK.", "KKSSKSSKHK.", "KRSSSSSSHK.",
        "KHKSSSSKHHK", "KHKgGGgKHHK", ".KGGGGGGGK.", "KSKGGGGGKSK", "KSKGGGGGKSK", ".KGGGGGGGK.",
        "KGGGGGGGGGK", ".KKKSKSKKK.", "...KFKFK...", "..KFFKFFK.."]
HEART = [".KK.KK.", "KRRKRRK", "KRRRRRK", ".KRRRK.", "..KRK..", "...K..."]
HEART_ROWS = [".RR.RR.", "RRRRRRR", "RRRRRRR", ".RRRRR.", "..RRR..", "...R..."]


def sprite(rows, pal_over=None):
    pal = dict(PAL, **(pal_over or {}))
    h, w = len(rows), len(rows[0])
    rgb = np.zeros((h, w, 3), np.float32)
    a = np.zeros((h, w), np.float32)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != ".":
                rgb[y, x] = hexc(pal[c])
                a[y, x] = 1
    return rgb, a


def put(F, spr, y, x, scale=1, mirror=False, amp=1.0):
    rgb, a = spr
    if mirror:
        rgb, a = rgb[:, ::-1], a[:, ::-1]
    if scale > 1:
        rgb = np.repeat(np.repeat(rgb, scale, 0), scale, 1)
        a = np.repeat(np.repeat(a, scale, 0), scale, 1)
    h, w = a.shape
    y, x = int(y), int(x)
    if y < 0 or x < 0 or y + h > F.shape[0] or x + w > F.shape[1]:
        return
    r = F[y:y + h, x:x + w]
    m = a[..., None] * amp
    r[:] = r * (1 - m) + rgb * m


def ptext(s, size=8):
    """Texto pixelado sin antialias (máscara 0/1 del tamaño justo)."""
    f = font("pixel", size)
    l, t, r, b = f.getbbox(s)
    img = Image.new("L", (r - l + 2, b - t + 2), 0)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((-l + 1, -t + 1), s, font=f, fill=255)
    return (np.asarray(img) > 127).astype(np.float32)


def put_text(F, s, cy, color, cx=LW / 2, size=8, shadow=True, amp=1.0, left=None):
    m = ptext(s, size)
    h, w = m.shape
    x = int(left if left is not None else cx - w / 2)
    y = int(cy - h / 2)
    if shadow:
        r = F[y + 1:y + 1 + h, x + 1:x + 1 + w]
        r *= 1 - m[..., None] * 0.8 * amp
    r = F[y:y + h, x:x + w]
    r[:] = r * (1 - m[..., None] * amp) + m[..., None] * hexc(color) * amp


BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16


class Theme:
    def __init__(self, special=False):
        self.special = special
        rng = np.random.default_rng(9)
        # cielo con tramado de 4 colores, como en los juegos de 16 bits
        cols = [hexc(c) for c in ("#140c34", "#2d1b69", "#5a2a82", "#a2457f", "#f08a6a")]
        y = np.arange(LH, dtype=np.float32)[:, None] / GROUND * (len(cols) - 1.2)
        y = np.clip(y, 0, len(cols) - 1.001)
        thr = np.tile(BAYER, (LH // 4 + 1, LW // 4 + 1))[:LH, :LW]
        idx = np.floor(y + (np.mod(y, 1) > thr)).astype(int).clip(0, len(cols) - 1)
        F = np.stack(cols)[idx]

        # luna, montañas escalonadas y suelo de pasto
        yy, xx = np.mgrid[0:LH, 0:LW]
        moon = (xx - 205) ** 2 + (yy - 210) ** 2 <= 15 ** 2
        F[moon] = hexc("#fff3c4")
        F[((xx - 211) ** 2 + (yy - 206) ** 2 <= 12 ** 2) & moon] = hexc("#ffe08a")
        for base, amp, col, per in ((400, 40, "#3a1d6e", 46), (430, 22, "#26124d", 28)):
            top = base - amp * np.abs(((xx[0] / per) % 2) - 1) - (xx[0] % 7 < 3) * 2
            F[yy > top[None, :]] = hexc(col)
        F[yy >= GROUND] = hexc("#6b3f22")
        F[(yy >= GROUND) & ((xx * 7 + yy * 3) % 11 == 0)] = hexc("#4f2d17")
        F[(yy >= GROUND) & (yy < GROUND + 6)] = hexc("#3fa34d")
        F[(yy >= GROUND) & (yy < GROUND + 2)] = hexc("#7ee07a")
        F[(yy == GROUND + 6) & (xx % 4 < 2)] = hexc("#3fa34d")
        F[yy >= GROUND + 40] = hexc("#140c1c")         # zona de HUD
        self.stars = [(int(rng.integers(0, 380)), int(rng.integers(0, LW)), rng.uniform(0, TAU),
                       int(rng.integers(1, 4)), rng.random() < 0.15) for _ in range(70)]

        # HUD
        put_text(F, "P1 JORGE", GROUND + 56, "#7cc4ff", left=14)
        put_text(F, "P2 ITZEL", GROUND + 56, "#ff8fb3", left=LW - 14 - 64)
        hs = sprite(HEART_ROWS, {"R": "#ff3d6e"})
        for i in range(3):
            put(F, hs, GROUND + 66, 14 + i * 9)
            put(F, hs, GROUND + 66, LW - 14 - 64 + i * 9)
        lvl = "NIVEL 5" if special else "NIVEL 4"
        put_text(F, f"{lvl} · {'5' if special else '4'} AÑOS JUNTOS", GROUND + 88, "#ffd166")
        F[GROUND + 98:GROUND + 104, 30:LW - 30] = hexc("#2a1b3d")
        self.bar = (GROUND + 99, 31, LW - 31)
        self.base = F

        self.boy = sprite(BOY)
        self.girl = sprite(GIRL)
        self.heart = sprite(HEART)
        self.confetti = [(rng.uniform(0, LW), rng.random(), int(rng.integers(1, 3)),
                          hexc(rng.choice(["#ffd166", "#ff5d8f", "#7cc4ff", "#7ee07a", "#ffffff"])),
                          rng.uniform(0, TAU)) for _ in range(90)]

    def frame(self, t):
        F = self.base.copy()
        a = TAU * t / T
        for y, x, ph, k, big in self.stars:
            on = math.sin(k * a + ph) > -0.3
            if on:
                F[y, x] = hexc("#ffffff")
                if big and math.sin(k * a * 2 + ph) > 0.4:
                    F[y - 1:y + 2, x] = hexc("#cfd8ff")
                    F[y, x - 1:x + 2] = hexc("#cfd8ff")

        # los dos personajes, respirando a destiempo
        bob1 = 1 if (t * 2) % 2 < 1 else 0
        bob2 = 1 if (t * 2 + 0.5) % 2 < 1 else 0
        put(F, self.boy, GROUND - 48 + bob1, 84, scale=3)
        put(F, self.girl, GROUND - 48 + bob2, 153, scale=3)

        # corazones que salen entre los dos
        for i in range(4):
            u = ((t / T) * 4 - i) % 4
            if u < 1.2:
                hy = GROUND - 62 - u * 90
                blink = u < 0.9 or int(t * 12) % 2
                if blink:
                    put(F, self.heart, hy, LW / 2 - 7 + 6 * math.sin(u * 6), scale=2)

        # barra de experiencia con un brillo que la recorre
        y0, x0, x1 = self.bar
        fill = x1 if self.special else int(x0 + (x1 - x0) * 0.8)
        F[y0:y0 + 4, x0:fill] = hexc("#ffd166")
        sh = int(x0 + ((t / T * 2) % 1) * (fill - x0))
        F[y0:y0 + 4, max(sh - 3, x0):sh] = hexc("#fff4c9")

        if self.special:
            if int(t * 3) % 2 == 0 or t > 2:
                put_text(F, "¡SUBISTE DE", 300, "#ffd166", size=16)
                put_text(F, "NIVEL!", 322, "#ffd166", size=16)
            put_text(F, "+1 AÑO DE AMOR", 352, "#ffffff")
            for x0c, y0c, k, col, ph in self.confetti:
                u = (y0c + k * t / T) % 1
                yy, xx = int(u * (GROUND - 10)), int(x0c + 6 * math.sin(u * 12 + ph)) % LW
                if math.sin(a * 8 + ph) > 0:
                    F[yy:yy + 2, xx:xx + 1] = col
                else:
                    F[yy:yy + 1, xx:xx + 2] = col
        else:
            if int(t * 2) % 2 == 0:
                put_text(F, "¡JUGADOR 2 SE HA UNIDO!", 320, "#ffffff")
            put_text(F, "PRESIONA ♥ PARA CONTINUAR", 350, "#ff8fb3", amp=0.85)

        big = cv2.resize(F, (W, H), interpolation=cv2.INTER_NEAREST)
        return np.clip(big * 255, 0, 255).astype(np.uint8)
