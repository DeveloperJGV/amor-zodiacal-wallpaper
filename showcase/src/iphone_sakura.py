"""Kit de prueba para iPhone del diseño Sakura.

El iPhone no acepta video de fondo, así que el kit son imágenes a resolución de iPhone:
  escena 3D (iOS 26), fotos aleatorias con mensajitos, fondo de inicio y clips para Live Photo.

    venv/Scripts/python showcase/src/iphone_sakura.py   -> showcase/out/iphone/sakura/
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, Patch, blur, hexc, over, over_img, text_mask, vgrad
from themes.t07_sakura import S, branch, flower, petal_sprites

W, H = 1290, 2796           # iPhone Pro Max; en los demás iPhone se ajusta solo
K = W / 1080                # escala respecto al diseño original
DEST = os.path.join(OUT, "iphone", "sakura")

# (nombre de archivo, líneas grandes, subtítulo, semilla de pétalos)
SHUFFLE = [
    ("01_nombres", [("Ana & Luis", 190)], "FLORECIENDO JUNTOS DESDE 2019", 1),
    ("02_te_quiero", [("Te quiero", 200)], "UN POQUITO MÁS QUE AYER", 2),
    ("03_pienso_en_ti", [("Pienso en ti", 180)], "TODO EL DÍA, TODOS LOS DÍAS", 3),
    ("04_favorita", [("Mi persona", 160), ("favorita", 170)], "ANA", 4),
    ("05_desde_2019", [("Desde 2019", 180)], "Y LO QUE NOS FALTA", 5),
    ("06_cumple_especial", [("Feliz cumpleaños,", 130), ("Ana", 190)], "QUE FLOREZCA TODO LO QUE QUIERES", 6),
]


def background(foreground_branch=False):
    """Cielo rosado con las ramas del diseño original, redibujadas a resolución de iPhone."""
    rng = np.random.default_rng(7)
    F = vgrad([(0, "#fff4f6"), (0.45, "#fbe1ea"), (1, "#f2bfd2")], w=W, h=H)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    F += np.exp(-((x - 850 * K) ** 2 + (y - 500 * K) ** 2) / (2 * (420 * K) ** 2))[..., None] * hexc("#fff3dc") * 0.25

    def layer(draw_fn):
        img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(img))
        a = np.asarray(img.resize((W, H), Image.LANCZOS), np.float32) / 255
        return a

    def ramas(d):
        tips = []
        branch(d, -40 * K, 900 * K, math.radians(8), 300 * K, 34 * K, 6, rng, tips)
        branch(d, W + 30 * K, 1330 * K, math.radians(170), 230 * K, 26 * K, 5, rng, tips)
        for tx, ty in tips:
            for _ in range(int(rng.integers(1, 3))):
                flower(d, tx + rng.normal(0, 16 * K), ty + rng.normal(0, 16 * K), rng.uniform(13, 22) * K, rng)

    def rama_frente(d):
        # rama grande y cercana que cruza la zona del reloj: es lo que el iPhone pone al frente en 3D
        tips = []
        branch(d, W + 60, 260, math.radians(196), 420, 58, 5, rng, tips)
        for tx, ty in tips:
            for _ in range(int(rng.integers(1, 3))):
                flower(d, tx + rng.normal(0, 26), ty + rng.normal(0, 26), rng.uniform(26, 42), rng)

    for fn in [ramas] + ([rama_frente] if foreground_branch else []):
        a = layer(fn)
        F *= 1 - blur(a[..., 3], 12 * K)[..., None] * 0.14
        F = F * (1 - a[..., 3:]) + a[..., :3] * a[..., 3:]
    return F


def petals(F, seed, n=80):
    """Pétalos congelados en el aire, distintos en cada imagen."""
    rng = np.random.default_rng(100 + seed)
    sprites = [petal_sprites(int(s * K), b * K) for s, b in [(9, 0), (12, 0), (16, 1.2), (24, 3.5)]]
    for _ in range(n):
        si = 3 if rng.random() < 0.08 else int(rng.integers(0, 3))
        spr = sprites[si][int(rng.integers(0, 24))]
        h, w = spr.shape[:2]
        over_img(F, int(rng.uniform(-60, H)) - h // 2, int(rng.uniform(-40, W + 40)) - w // 2, spr,
                 rng.uniform(0.75, 1.0))


def write_text(F, lines, sub):
    y = 1680 * K - (len(lines) - 1) * 85 * K
    for s, size in lines:
        m = text_mask(s, "vibes", int(size * K), cx=W / 2, cy=y, w=W, h=H)
        over(F, Patch(blur(m, 3 * K)), hexc("#ffffff"), 0.5)
        over(F, Patch(m), hexc("#9c3456"), 0.95)
        y += 170 * K
    over(F, Patch(text_mask(sub, "mont", int(26 * K), cx=W / 2, cy=y + 10 * K, wght=500, tracking=8 * K, w=W, h=H)),
         hexc("#b5577a"), 0.85)


def save(F, name):
    dither = np.random.default_rng(7).random((H, W, 1)).astype(np.float32) - 0.5
    img = Image.fromarray(np.clip(F * 255 + dither, 0, 255).astype(np.uint8))
    path = os.path.join(DEST, name + ".jpg")
    img.save(path, quality=93, subsampling=0)
    print(path)


def live_clips():
    """Clips de 3 s para convertir en Live Photo (se mueve al prender la pantalla)."""
    src = os.path.join(OUT, "wallpapers")
    for name, video in (("live_normal", "t07_sakura.mp4"), ("live_cumple", "t07_sakura_especial.mp4")):
        path = os.path.join(DEST, name + ".mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(src, video), "-t", "3",
                        "-vf", f"scale={W}:{H}:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", path], check=True)
        print(path)


def main():
    os.makedirs(DEST, exist_ok=True)
    base = background()
    for name, lines, sub, seed in SHUFFLE:
        F = base.copy()
        petals(F, seed, 140 if "especial" in name else 80)
        write_text(F, lines, sub)
        save(F, "aleatorio_" + name)

    # escena 3D: la rama grande al frente cruza el reloj
    F = background(foreground_branch=True)
    petals(F, 9)
    write_text(F, *SHUFFLE[0][1:3])
    save(F, "escena_3d")

    # pantalla de inicio: el mismo cielo, suave, para que los íconos se lean
    F = blur(base, 22) * 0.96 + 0.04
    save(F, "inicio")
    live_clips()


if __name__ == "__main__":
    main()
