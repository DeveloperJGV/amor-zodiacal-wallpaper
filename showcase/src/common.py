"""Utilidades compartidas por los 10 wallpapers de muestra.

Cada tema es una clase Theme(special=False) con .frame(t) -> uint8 (H, W, 3).
Todo el movimiento es periódico en T segundos, así el video hace loop perfecto.
`special` activa la sorpresa de fecha (aniversario, 14 de febrero, etc.).
"""
import math, os, subprocess
from functools import lru_cache
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(ROOT, "fonts")
OUT = os.path.join(ROOT, "out")

# WP_SIZE=1920x1080 para las versiones de escritorio (los temas que lo soportan)
W, H = (int(v) for v in os.environ.get("WP_SIZE", "1080x2340").split("x"))
FPS = 30
T = 10.0
TAU = 2 * math.pi

FONT_FILES = {
    "vibes": "GreatVibes-Regular.ttf",
    "dancing": "DancingScript[wght].ttf",
    "playfair": "PlayfairDisplay[wght].ttf",
    "playfair-i": "PlayfairDisplay-Italic[wght].ttf",
    "mont": "Montserrat[wght].ttf",
    "pixel": "PressStart2P-Regular.ttf",
    "pacifico": "Pacifico-Regular.ttf",
    "caveat": "Caveat[wght].ttf",
    "sacramento": "Sacramento-Regular.ttf",
    "orbitron": "Orbitron[wght].ttf",
    "quick": "Quicksand[wght].ttf",
}


# ---------------------------------------------------------------- curvas de tiempo

def sm(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def window(t, a, b, fade):
    """1 entre a y b, con entradas/salidas suaves de `fade` segundos."""
    return sm((t - a) / fade) * sm((b - t) / fade)


def wave(t, k=1, phase=0.0):
    """Seno que da k vueltas exactas por ciclo (loop perfecto), en 0..1."""
    return 0.5 + 0.5 * np.sin(TAU * k * t / T + phase)


# ---------------------------------------------------------------- texto

@lru_cache(None)
def font(name, size, wght=None):
    f = ImageFont.truetype(os.path.join(FONTS, FONT_FILES[name]), size)
    if wght is not None:
        try:
            f.set_variation_by_axes([wght])
        except OSError:
            pass
    return f


def text_mask(text, name, size, cx=W / 2, cy=H / 2, wght=None, tracking=0, w=W, h=H, stroke=0, align="center",
              left=None):
    """Máscara float (h, w) del texto centrado en (cx, cy), o desde x=left. tracking en px entre letras."""
    f = font(name, size, wght)
    if left is not None:
        cx = left + f.getlength(text) / 2
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    if tracking and "\n" not in text:
        widths = [f.getlength(c) for c in text]
        total = sum(widths) + tracking * (len(text) - 1)
        x = cx - total / 2
        for c, cw in zip(text, widths):
            d.text((x, cy), c, font=f, fill=255, anchor="lm", stroke_width=stroke, stroke_fill=255)
            x += cw + tracking
    else:
        d.multiline_text((cx, cy), text, font=f, fill=255, anchor="mm", align=align,
                         stroke_width=stroke, stroke_fill=255, spacing=size * 0.25)
    return np.asarray(img, np.float32) / 255


# ---------------------------------------------------------------- máscaras y capas

def blur(m, sigma):
    return cv2.GaussianBlur(m, (0, 0), sigma)


class Patch:
    """Recorte de una máscara grande: sólo se compone la zona que tiene algo."""

    def __init__(self, m, margin=0):
        ys, xs = np.nonzero(m > 1 / 512)
        if len(ys) == 0:
            self.y0 = self.x0 = 0
            self.a = np.zeros((1, 1), np.float32)
            return
        y0, y1 = max(ys.min() - margin, 0), min(ys.max() + 1 + margin, m.shape[0])
        x0, x1 = max(xs.min() - margin, 0), min(xs.max() + 1 + margin, m.shape[1])
        self.y0, self.x0 = y0, x0
        self.a = np.ascontiguousarray(m[y0:y1, x0:x1], np.float32)

    def region(self, F):
        h, w = self.a.shape
        return F[self.y0:self.y0 + h, self.x0:self.x0 + w]


def glow_patch(m, sigma, margin=None):
    margin = int(sigma * 3) if margin is None else margin
    p = Patch(m)
    h, w = p.a.shape
    big = np.zeros((h + 2 * margin, w + 2 * margin), np.float32)
    big[margin:margin + h, margin:margin + w] = p.a
    big = blur(big, sigma)
    out = Patch(np.zeros((1, 1)))
    out.y0, out.x0 = p.y0 - margin, p.x0 - margin
    # recortar a la pantalla
    cy0, cx0 = max(-out.y0, 0), max(-out.x0, 0)
    out.a = big[cy0:, cx0:]
    out.y0, out.x0 = out.y0 + cy0, out.x0 + cx0
    out.a = out.a[:H - out.y0, :W - out.x0]
    return out


def add(F, p, color, amp=1.0):
    if amp <= 0:
        return
    r = p.region(F)
    a = p.a[:r.shape[0], :r.shape[1]]
    r += a[..., None] * (np.asarray(color, np.float32) * amp)


def over(F, p, color, amp=1.0):
    if amp <= 0:
        return
    r = p.region(F)
    a = p.a[:r.shape[0], :r.shape[1], None] * amp
    r *= 1 - a
    r += a * np.asarray(color, np.float32)


def over_img(F, y0, x0, rgba, amp=1.0):
    """Compone una imagen RGBA float (h, w, 4) en (y0, x0), recortando bordes."""
    h, w = rgba.shape[:2]
    sy0, sx0 = max(-y0, 0), max(-x0, 0)
    sy1, sx1 = min(h, F.shape[0] - y0), min(w, F.shape[1] - x0)
    if sy1 <= sy0 or sx1 <= sx0:
        return
    src = rgba[sy0:sy1, sx0:sx1]
    r = F[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1]
    a = src[..., 3:4] * amp
    r *= 1 - a
    r += src[..., :3] * a


@lru_cache(None)
def gauss_sprite(sig):
    r = int(math.ceil(sig * 3.5))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return np.exp(-(x * x + y * y) / (2 * sig * sig)).astype(np.float32)


@lru_cache(None)
def flare_sprite(rad, thick=1.2):
    """Destello en cruz para estrellas grandes."""
    r = int(rad)
    y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    d = np.hypot(x, y) + 1e-3
    core = np.exp(-d * d / (2 * (rad * 0.08) ** 2))
    rays = (np.exp(-x * x / (2 * thick ** 2)) + np.exp(-y * y / (2 * thick ** 2))) * np.clip(1 - d / rad, 0, 1) ** 2
    halo = np.exp(-d / (rad * 0.18)) * 0.35
    return (core + rays * 0.6 + halo).astype(np.float32)


def blit(F, spr, cy, cx, color, amp=1.0):
    """Suma un sprite centrado en (cy, cx)."""
    if amp <= 0:
        return
    h, w = spr.shape
    y0, x0 = int(round(cy)) - h // 2, int(round(cx)) - w // 2
    sy0, sx0 = max(-y0, 0), max(-x0, 0)
    sy1, sx1 = min(h, F.shape[0] - y0), min(w, F.shape[1] - x0)
    if sy1 <= sy0 or sx1 <= sx0:
        return
    F[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] += spr[sy0:sy1, sx0:sx1, None] * (np.asarray(color, np.float32) * amp)


# ---------------------------------------------------------------- formas

def hexc(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def vgrad(stops, w=W, h=H):
    """Degradado vertical. stops: [(posición 0..1, '#rrggbb'), ...]."""
    pos = np.array([p for p, _ in stops])
    cols = np.array([hexc(c) for _, c in stops])
    y = np.linspace(0, 1, h)
    col = np.stack([np.interp(y, pos, cols[:, c]) for c in range(3)], -1).astype(np.float32)
    return np.repeat(col[:, None, :], w, 1)


def heart_points(n=200):
    t = np.linspace(0, TAU, n, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    return np.stack([x / 17, (y + 2.5) / 17], -1)  # aprox. en [-1, 1]


def heart_mask(size, cx=None, cy=None, w=None, h=None, outline=0):
    """Corazón relleno (o contorno de `outline` px) de ancho ~size."""
    w = w or size + 4
    h = h or size + 4
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    pts = heart_points() * size / 2 + [cx, cy]
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    if outline:
        d.line([tuple(p) for p in np.vstack([pts, pts[:1]])], fill=255, width=outline, joint="curve")
    else:
        d.polygon([tuple(p) for p in pts], fill=255)
    return np.asarray(img, np.float32) / 255


def sample_points(mask, n, rng, thr=0.5):
    ys, xs = np.nonzero(mask > thr)
    idx = rng.choice(len(ys), n, replace=len(ys) < n)
    return np.stack([ys[idx], xs[idx]], -1).astype(np.float32)


def spread_points(mask, n, rng, thr=0.5, pool=20):
    """Puntos repartidos parejo sobre la máscara (muestreo del más lejano)."""
    cand = sample_points(mask, n * pool, rng, thr)
    pts = [cand[0]]
    d = np.full(len(cand), np.inf)
    for _ in range(n - 1):
        d = np.minimum(d, ((cand - pts[-1]) ** 2).sum(1))
        pts.append(cand[np.argmax(d)])
    return np.array(pts)


def vignette(strength=0.5, w=W, h=H):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((x - w / 2) / (w * 0.75), (y - h / 2) / (h * 0.6))
    return (1 - strength * np.clip(d, 0, 1.4) ** 2 / 1.96).astype(np.float32)[..., None]


_DITHER = np.random.default_rng(7).random((H, W, 1)).astype(np.float32) - 0.5


def finish(F):
    """Float 0..1 -> uint8, con un tramado fijo para que los degradados no hagan bandas."""
    return np.clip(F * 255 + _DITHER, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- video

def encode(frames, path, w=W, h=H, fps=FPS, crf=16):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
    for fr in frames:
        ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    ff.wait()
