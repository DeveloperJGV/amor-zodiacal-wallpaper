"""Analiza la ilustración original y separa cada elemento del dibujo.

Produce build/seg_v2.pkl con:
  im, bg      imagen recortada a 1080x2340 y su fondo limpio (sin trazos)
  ink, lab    máscara de trazo y etiquetas de componentes
  comps       lista de elementos clasificados: dot, spark, heart, sign, line
  paths       para cada 'line', su recorrido ordenado (para los cometas)
"""
import os, pickle
from collections import Counter, deque
import numpy as np
from PIL import Image
from scipy import ndimage as nd
from skimage.morphology import skeletonize

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "Wallpaper001.jpeg")
OUT = os.path.join(ROOT, "build", "seg_v2.pkl")
W, H = 1080, 2340


def load_cropped():
    src = Image.open(SRC).convert("RGB")
    s = H / src.height
    src = src.resize((round(src.width * s), H), Image.LANCZOS)
    x0 = (src.width - W) // 2
    return np.asarray(src.crop((x0, 0, x0 + W, H))).astype(np.float32)


def clean_background(im):
    small = im[::4, ::4]
    bg = np.stack([nd.median_filter(small[..., c], size=45) for c in range(3)], -1)
    bg = nd.zoom(bg, (H / bg.shape[0], W / bg.shape[1], 1), order=1)
    return nd.gaussian_filter(bg, (6, 6, 0))


def classify(area, h, w):
    fill = area / (h * w)
    if area < 60:
        return "dot"
    if max(h, w) > 260 or fill < 0.2:
        return "line"
    if fill > 0.55 and abs(h - w) < 0.35 * max(h, w):
        return "heart" if area > 500 else "dot"
    if fill < 0.45 and h > w * 1.15 and max(h, w) < 90:
        return "spark"
    if area > 2500:
        return "sign"
    return "line"


def longest_path(skel):
    """Recorrido más largo dentro de un esqueleto (doble BFS)."""
    pts = [tuple(p) for p in np.argwhere(skel)]
    if len(pts) < 2:
        return np.array(pts)
    idx = set(pts)

    def nbrs(p):
        y, x = p
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                q = (y + dy, x + dx)
                if q != p and q in idx:
                    yield q

    def bfs(start):
        par = {start: None}
        dq = deque([start])
        last = start
        while dq:
            last = dq.popleft()
            for q in nbrs(last):
                if q not in par:
                    par[q] = last
                    dq.append(q)
        return last, par

    a, _ = bfs(pts[0])
    b, par = bfs(a)
    path = []
    while b is not None:
        path.append(b)
        b = par[b]
    return np.array(path[::-1])


def main():
    im = load_cropped()
    bg = clean_background(im)
    d = im.mean(2) - bg.mean(2)
    ink = np.clip((d - 2) / 14, 0, 1)
    binary = nd.binary_fill_holes(nd.binary_closing(ink > 0.25, iterations=2))
    lab, n = nd.label(binary)
    comps, paths = [], []
    for i, sl in enumerate(nd.find_objects(lab)):
        m = lab[sl] == i + 1
        area = int(m.sum())
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        k = classify(area, h, w)
        comps.append(dict(sl=sl, k=k, area=area,
                          cy=(sl[0].start + sl[0].stop) / 2, cx=(sl[1].start + sl[1].stop) / 2))
    # Los caminos son guiones separados: se engrosan para unirlos en curvas continuas.
    keep = np.zeros(len(comps) + 1, bool)
    for i, c in enumerate(comps):
        keep[i + 1] = c["k"] in ("line", "dot")
    strokes = keep[lab]
    blobs, nb = nd.label(nd.binary_dilation(strokes, iterations=6))
    for j, sl in enumerate(nd.find_objects(blobs)):
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) < 150:
            continue
        blob = blobs[sl] == j + 1
        p = longest_path(skeletonize(blob))
        if len(p) < 50:
            continue
        s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
        pm = np.zeros_like(blob)
        pm[p[:, 0], p[:, 1]] = True
        sgrid = np.full(blob.shape, np.nan, np.float32)
        sgrid[p[:, 0], p[:, 1]] = s
        _, (iy, ix) = nd.distance_transform_edt(~pm, return_indices=True)
        smap = np.where(blob & strokes[sl], sgrid[iy, ix], np.nan).astype(np.float32)
        paths.append(dict(sl=sl, path=p + [sl[0].start, sl[1].start], s=s, length=float(s[-1]), smap=smap))
    print(n, Counter(c["k"] for c in comps), "caminos:", len(paths),
          "largos>300px:", sum(v["length"] > 300 for v in paths))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pickle.dump(dict(im=im, bg=bg, ink=ink, lab=lab, comps=comps, paths=paths), open(OUT, "wb"))


if __name__ == "__main__":
    main()
