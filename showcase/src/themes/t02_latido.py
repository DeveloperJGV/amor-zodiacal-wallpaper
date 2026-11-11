"""02 · Latido: un monitor cardiaco de neón cuya línea dibuja un corazón.

Personalizable: nombres, fecha, las pulsaciones.
Sorpresa (14 de febrero): el corazón se llena de luz y suben corazones por la pantalla.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd
from common import (W, H, T, TAU, Patch, add, blit, blur, flare_sprite, glow_patch, heart_mask, heart_points,
                    hexc, sm, text_mask, vgrad, vignette, window, finish)

TITLE = "Latido"
CAPTION = "Su corazón late en tu pantalla"
SPECIAL = "El 14 de febrero, el corazón se enciende"

Y0, BH = 1080, 520           # banda donde vive la línea
BASE = 330                   # línea base dentro de la banda
PINK = hexc("#ff2e7e")
CORE = hexc("#ffd6e6")
CYAN = hexc("#7af0ff")
SWEEP = 5.0                  # segundos por barrido (2 por ciclo)


def beat(x0):
    """Complejo P-QRS-T empezando en x0, como lista de (x, dy)."""
    return [(x0, 0), (x0 + 18, -14), (x0 + 36, 0), (x0 + 60, 0), (x0 + 70, 18), (x0 + 86, -190),
            (x0 + 102, 52), (x0 + 114, 0), (x0 + 150, 0), (x0 + 178, -26), (x0 + 206, 0)]


def build_path():
    pts = [(-30, 0), (60, 0)] + beat(70)
    pts += [(410, 0), (540, 0)]
    hp = heart_points(400)                           # empieza arriba al centro
    hp = np.roll(hp, -200, 0)                        # que empiece en la punta de abajo
    hp = (hp - hp[0]) * [150, 150]                   # punta en (0, 0)
    hp[:, 1] *= 1.0
    pts += [(540 + x, y) for x, y in hp] + [(540, 0), (680, 0)]
    pts += beat(720) + [(1000, 0), (W + 30, 0)]
    p = np.array(pts, np.float64)
    seg = np.hypot(*np.diff(p, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    ss = np.arange(0, s[-1], 1.0)
    return np.stack([np.interp(ss, s, p[:, 0]), np.interp(ss, s, p[:, 1]) + BASE], -1), ss


class Theme:
    def __init__(self, special=False):
        self.special = special
        rng = np.random.default_rng(2)
        F = vgrad([(0, "#040106"), (0.5, "#12041a"), (1, "#060108")])
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        F += np.exp(-((x - 540) ** 2 + (y - 1300) ** 2) / (2 * 520 ** 2))[..., None] * hexc("#5a0d3a") * 0.5
        grid = ((x % 54 < 1.5) | (y % 54 < 1.5)).astype(np.float32)
        F += grid[..., None] * hexc("#ff2e7e") * 0.035
        F *= vignette(0.6)

        # la línea y su mapa de "distancia recorrida" (s) por pixel
        path, s = build_path()
        self.path, self.L = path, s[-1]
        img = Image.new("L", (W, BH), 0)
        ImageDraw.Draw(img).line([tuple(q) for q in path], fill=255, width=5, joint="curve")
        self.line = np.asarray(img, np.float32) / 255
        idx = np.full((BH, W), -1, np.int64)
        py = np.clip(np.round(path[:, 1]).astype(int), 0, BH - 1)
        px = np.clip(np.round(path[:, 0]).astype(int), 0, W - 1)
        idx[py, px] = np.arange(len(path))
        _, (iy, ix) = nd.distance_transform_edt(idx < 0, return_indices=True)
        self.smap = s[idx[iy, ix]].astype(np.float32)
        self.spikes = [s[np.argmin(np.abs(path[:, 0] - 156) + (path[:, 1] > BASE - 150) * 1e4)],
                       s[np.argmin(np.abs(path[:, 0] - 806) + (path[:, 1] > BASE - 150) * 1e4)]]

        # textos de neón (con su resplandor fijo)
        sub = "FELIZ 14 DE FEBRERO" if special else "DESDE EL 03.08.2020"
        names = text_mask("MARIANA & DIEGO", "orbitron", 60, cy=1730, wght=700, tracking=8)
        self.names = Patch(names)
        self.names_glow = glow_patch(names, 14)
        add(F, Patch(text_mask(sub, "orbitron", 28, cy=1820, wght=500, tracking=7)), CYAN, 0.75)
        add(F, Patch(text_mask("mi corazón late por ti", "caveat", 64, cy=1930, wght=500)), CORE, 0.55)

        # monitor: corazoncito y LPM
        hm = heart_mask(44, cx=760, cy=962, w=W, h=H)
        self.bpm_heart = Patch(hm)
        self.bpm_glow = glow_patch(hm, 10)
        add(F, Patch(text_mask("72", "orbitron", 64, cx=860, cy=960, wght=600)), PINK, 0.9)
        add(F, Patch(text_mask("LPM", "orbitron", 24, cx=950, cy=975, wght=500)), PINK, 0.6)
        add(F, Patch(text_mask("ECG  II", "orbitron", 22, cx=170, cy=965, wght=500, tracking=4)), CYAN, 0.5)
        self.base = F

        # sorpresa: el corazón relleno y corazones que suben
        fill = Image.new("L", (W, BH), 0)
        hp = path[(path[:, 0] > 380) & (path[:, 1] < BASE - 2)]
        ImageDraw.Draw(fill).polygon([tuple(q) for q in hp], fill=255)
        f = np.zeros((H, W), np.float32)
        f[Y0:Y0 + BH] = np.asarray(fill, np.float32) / 255
        self.fill = Patch(blur(f, 2))
        self.fill_glow = glow_patch(f, 40)
        self.floaters = [(rng.random() * W, rng.random(), int(rng.integers(1, 3)), 18 + 30 * rng.random(),
                          rng.random() * TAU) for _ in range(22)]
        self.small_hearts = {s: heart_mask(s) for s in range(18, 50, 2)}

    def frame(self, t):
        F = self.base.copy()
        head = (t % SWEEP) / SWEEP * (self.L + 300)
        lag = head - self.smap
        lag = np.where(lag < 0, lag + self.L + 300, lag)
        I = self.line * (0.06 + 0.94 * np.exp(-lag / 650))
        band = F[Y0:Y0 + BH]
        band += I[..., None] * CORE * 0.9
        band += blur(I, 5)[..., None] * PINK * 1.4
        band += blur(I, 22)[..., None] * PINK * 0.9
        if head < self.L:
            k = int(min(head, len(self.path) - 1))
            hx, hy = self.path[k]
            blit(F, flare_sprite(46), Y0 + hy, hx, CORE, 1.0)

        # el corazoncito late cuando pasa el pico
        pulse = sum(math.exp(-((head - sp) / 70) ** 2) for sp in self.spikes)
        add(F, self.bpm_heart, PINK, 0.45 + 0.55 * pulse)
        add(F, self.bpm_glow, PINK, 0.25 + 0.6 * pulse)

        # nombres de neón con un parpadeo de vez en cuando
        flick = 1.0
        if 3.05 < t < 3.35:
            flick = 0.35 if int(t * 40) % 3 else 0.9
        add(F, self.names, CORE, 0.95 * flick)
        add(F, self.names_glow, PINK, 1.1 * flick)

        if self.special:
            g = 0.6 + 0.4 * math.sin(TAU * 5 * t / T) ** 2
            add(F, self.fill, PINK, 0.55 * g)
            add(F, self.fill_glow, PINK, 0.5 * g)
            for x0, y0, k, size, ph in self.floaters:
                u = (y0 + k * t / T) % 1
                y = H + 60 - u * (H + 120)
                x = x0 + 30 * math.sin(TAU * u * 2 + ph)
                m = self.small_hearts[int(size) // 2 * 2]
                a = 0.5 * sm(u / 0.1) * sm((1 - u) / 0.3)
                blit(F, m, y, x, PINK, a)
        return finish(F)
