"""Renderiza los wallpapers de muestra.

  python showcase/src/build.py                      todos, normal y sorpresa -> showcase/out/
  python showcase/src/build.py 03 07                sólo esos temas
  python showcase/src/build.py 03 --preview 0 4 8   cuadros sueltos en PNG (para revisar rápido)
  python showcase/src/build.py --special ...        la versión de fecha especial
  WP_SIZE=1920x1080 python showcase/src/build.py 05 08   versión de escritorio -> showcase/out/escritorio/
"""
import argparse, importlib, os, sys, time
from multiprocessing import Pool
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, FPS, T, W, H, encode  # noqa: E402

DESKTOP = W > H
OUT_DIR = os.path.join(OUT, "escritorio" if DESKTOP else "wallpapers")

THEMES = sorted(f[:-3] for f in os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes"))
                if f.startswith("t") and f.endswith(".py"))


def load(key):
    name = next(n for n in THEMES if n[1:3] == key or n == key)
    return name, importlib.import_module(f"themes.{name}").Theme


def render(job):
    key, special = job
    name, Theme = load(key)
    th = Theme(special=special)
    path = os.path.join(OUT_DIR, f"{name}{'_especial' if special else ''}.mp4")
    t0 = time.time()
    encode((th.frame(i / FPS) for i in range(int(T * FPS))), path)
    return f"{path}  ({time.time() - t0:.0f} s)"


def preview(key, special, times):
    name, Theme = load(key)
    th = Theme(special=special)
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    for t in times:
        t0 = time.time()
        fr = th.frame(t)
        dt = time.time() - t0
        p = os.path.join(OUT, "preview", f"{name}{'_s' if special else ''}_{t:g}.png")
        Image.fromarray(fr).resize((W // 2, H // 2), Image.LANCZOS).save(p)
        print(p, f"{dt:.2f} s/cuadro")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("themes", nargs="*")
    ap.add_argument("--special", action="store_true")
    ap.add_argument("--both", action="store_true", help="normal y especial")
    ap.add_argument("--preview", nargs="*", type=float)
    a = ap.parse_args()
    keys = a.themes or [n[1:3] for n in THEMES]
    if a.preview is not None:
        for k in keys:
            preview(k, a.special, a.preview or [0, 3, 6])
        return
    modes = [False, True] if (a.both or not a.themes) else [a.special]
    jobs = [(k, s) for k in keys for s in modes]
    with Pool(min(len(jobs), max(os.cpu_count() - 1, 1))) as pool:
        for r in pool.imap_unordered(render, jobs):
            print(r, flush=True)


if __name__ == "__main__":
    main()
