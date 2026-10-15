"""Genera el proyecto Scene de Wallpaper Engine (v3, interactivo).

  python src/v3/build_scene.py [--install]

Crea build/v3/amor_zodiacal_v3 con scene.json, modelos, materiales y texturas .tex
(escritas directamente, sin pasar por el editor). Con --install lo copia a
projects/myprojects de Wallpaper Engine.
"""
import json, math, os, pickle, shutil, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src", "v2"))
sys.path.insert(0, HERE)
from glyphs import GLYPHS  # noqa: E402
from render import blit, flare_sprite, gauss_sprite, GLOW, GOLD, WHITE, MORSE, MORSE_TEXT  # noqa: E402
from tex import write_tex  # noqa: E402

OUT = os.path.join(ROOT, "build", "v3", "amor_zodiacal_v3")
WE = r"C:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
T = 30.0

MESSAGES = {  # id: (líneas, alto de letra, centro y, inicio)
    "jc": (["J♥C"], 215, 1090, 2.5),
    "teamo": (["TE AMO"], 150, 1170, 12.5),
    "fecha": (["18·10·25"], 118, 1250, 22.0),
    "aniv": (["FELIZ", "ANIVERSARIO"], 105, 1200, 22.0),
}
NORMAL = ["jc", "teamo", "fecha"]
ANNIV = ["jc", "teamo", "aniv"]

DEPTH = dict(base=0.0, sign=0.55, heart=0.8, spark=0.65, glyph=1.0, fx=0.0)


class Builder:
    def __init__(self):
        if os.path.exists(OUT):
            shutil.rmtree(OUT)
        for d in ("models", "materials/az"):
            os.makedirs(os.path.join(OUT, d))
        self.objects = []
        self.layers = []
        self.nid = 10

    def image(self, name, rgba, cx, cy, blending="translucent", depth=0.0, alpha=1.0, scale=1.0, solid=False, script=None):
        """Añade una capa de imagen centrada en (cx, cy) en coordenadas de imagen (y hacia abajo)."""
        rgba = np.clip(rgba, 0, 255).astype(np.uint8)
        h, w = rgba.shape[:2]
        write_tex(os.path.join(OUT, "materials", "az", name + ".tex"), rgba)
        mat = {"passes": [{"blending": blending, "combos": {"version": 2}, "cullmode": "nocull",
                           "depthtest": "disabled", "depthwrite": "disabled",
                           "shader": "genericimage2", "textures": ["az/" + name]}]}
        json.dump(mat, open(os.path.join(OUT, "materials", "az", name + ".json"), "w"), indent=1)
        json.dump({"autosize": True, "material": f"materials/az/{name}.json"},
                  open(os.path.join(OUT, "models", name + ".json"), "w"), indent=1)
        self.nid += 1
        obj = {"id": self.nid, "name": name, "image": f"models/{name}.json",
               "origin": f"{cx:.2f} {self.H - cy:.2f} 0.00000", "angles": "0.00000 0.00000 0.00000",
               "scale": f"{scale:.5f} {scale:.5f} 1.00000", "size": f"{w:.5f} {h:.5f}",
               "alignment": "center", "alpha": alpha, "brightness": 1.0, "color": "1.00000 1.00000 1.00000",
               "colorBlendMode": 0, "copybackground": True, "ledsource": False, "locktransforms": False,
               "parallaxDepth": f"{depth:.5f} {depth:.5f}", "perspective": False, "solid": solid,
               "visible": True}
        if script:
            obj["visible"] = {"script": script, "value": True}
        self.objects.append(obj)
        self.layers.append(name)
        return name


def additive(rgb):
    """rgb float (0..255) -> rgba con alfa = brillo, color sin premultiplicar."""
    a = np.clip(rgb.max(-1, keepdims=True), 0, 255)
    col = np.where(a > 0.5, rgb / np.maximum(a, 1e-3) * 255, 0)
    return np.concatenate([col, a], -1)


def glyph_strokes(text_lines, hgt, cy, W):
    """Lista de (trazos) por glifo en pixeles, para un mensaje de 1 o más líneas."""
    out = []
    n = len(text_lines)
    for li, text in enumerate(text_lines):
        y_c = cy + (li - (n - 1) / 2) * hgt * 1.45
        sp = 0.22
        total = sum(GLYPHS[c][0] for c in text) + sp * (len(text) - 1)
        x = W / 2 - total * hgt / 2
        y0 = y_c - hgt / 2
        for c in text:
            adv, strk = GLYPHS[c]
            if strk:
                g = []
                for s in strk:
                    pts = []
                    for px, py in s:
                        q = (x + px * hgt, y0 + py * hgt)
                        if not pts or math.dist(pts[-1], q) > 0.06 * hgt:
                            pts.append(q)
                    g.append(pts)
                out.append(g)
            x += (adv + sp) * hgt
    return out


def render_glyph(strokes):
    xs = [q[0] for s in strokes for q in s]
    ys = [q[1] for s in strokes for q in s]
    m = 40
    x0, y0 = int(min(xs)) - m, int(min(ys)) - m
    x1, y1 = int(max(xs)) + m, int(max(ys)) + m
    S = 3
    cv = Image.new("L", ((x1 - x0) * S, (y1 - y0) * S), 0)
    d = ImageDraw.Draw(cv)
    for s in strokes:
        if len(s) > 1:
            d.line([((q[0] - x0) * S, (q[1] - y0) * S) for q in s], fill=255, width=S * 2, joint="curve")
    lines = np.asarray(cv.resize((x1 - x0, y1 - y0), Image.BOX), np.float32) / 255
    glow = nd.gaussian_filter(lines, 6)
    rgb = (lines * 150)[..., None] * GOLD + (glow * 190)[..., None] * GLOW
    big = flare_sprite(22) + 0.6 * np.pad(gauss_sprite(3.2), 22 - gauss_sprite(3.2).shape[0] // 2)
    small = flare_sprite(13) + 0.5 * np.pad(gauss_sprite(2.4), 13 - gauss_sprite(2.4).shape[0] // 2)
    for s in strokes:
        for i, q in enumerate(s):
            spr = big if (i == 0 or i == len(s) - 1) else small
            r = spr.shape[0] // 2
            cy, cx = int(round(q[1] - y0)), int(round(q[0] - x0))
            rgb[cy - r:cy + r + 1, cx - r:cx + r + 1] += (spr * 230)[..., None] * WHITE
    return additive(rgb), (x0 + x1) / 2, (y0 + y1) / 2


def heart_shape(size):
    S = 4
    cv = Image.new("L", (size * S, size * S), 0)
    pts = []
    for i in range(80):
        t = 2 * math.pi * i / 80
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(((0.5 + x / 44) * size * S, (0.46 - y / 44) * size * S))
    ImageDraw.Draw(cv).polygon(pts, fill=255)
    return np.asarray(cv.resize((size, size), Image.LANCZOS), np.float32) / 255


def main():
    D = pickle.load(open(os.path.join(ROOT, "build", "seg_v2.pkl"), "rb"))
    im, bg, ink, lab, comps, paths = D["im"], D["bg"], D["ink"], D["lab"], D["comps"], D["paths"]
    H, W = im.shape[:2]
    B = Builder()
    B.H = H
    rng = np.random.default_rng(2025)
    res = im - bg
    zone = lambda y: 0.45 + 0.55 * min(max((y - 300) / 500, 0), 1)

    # elementos que se vuelven capas propias (se quitan de la base)
    sel = [i for i, c in enumerate(comps) if c["k"] in ("sign", "heart", "spark")]
    base = im.copy()
    crops = {}
    for i in sel:
        c = comps[i]
        m = {"heart": 30, "sign": 26, "spark": 24}[c["k"]]
        sl0 = c["sl"]
        sl = (slice(max(sl0[0].start - m, 0), min(sl0[0].stop + m, H)),
              slice(max(sl0[1].start - m, 0), min(sl0[1].stop + m, W)))
        msk = nd.binary_dilation(lab[sl] == i + 1, iterations=3)
        base[sl] -= res[sl] * msk[..., None]
        crops[i] = (sl, msk)
    top = (0.86 + 0.14 * np.clip(np.arange(H) / 700, 0, 1))[:, None, None]
    base = base * top
    rgba = np.concatenate([base, np.full((H, W, 1), 255.0)], -1)
    # la base es sólida (recibe los toques) y lleva el script director
    base_name = B.image("base", rgba, W / 2, H / 2, depth=DEPTH["base"], solid=True, script="__DIRECTOR__")

    data = dict(H=H, sparks=[], hearts=[], signs=[], taps=[], flashes=[], comet=[], paths=[], comets=[])
    morse_i = None
    big_sparks = [i for i in sel if comps[i]["k"] == "spark" and comps[i]["area"] > 250]
    morse_i = min(big_sparks, key=lambda i: (comps[i]["cx"] - 800) ** 2 + (comps[i]["cy"] - 1880) ** 2)

    for i in sel:
        c = comps[i]
        k = c["k"]
        sl, msk = crops[i]
        cy = (sl[0].start + sl[0].stop) / 2
        cx = (sl[1].start + sl[1].stop) / 2
        art = im[sl] * top[sl[0]]
        a = np.clip(ink[sl] * 1.25, 0, 1) * msk
        a = nd.gaussian_filter(a, 0.6) * msk
        layer = np.concatenate([art, (a * 255)[..., None]], -1)
        blur = nd.gaussian_filter((ink[sl] * msk).astype(np.float32), {"heart": 12, "sign": 10, "spark": 7}[k])
        blur /= max(blur.max(), 1e-3)
        lit = np.clip(res[sl], 0, None) * msk[..., None]
        z = zone(c["cy"])
        nm = f"{k}{i}"
        B.image(nm, layer, cx, cy, depth=DEPTH[k])
        if k == "spark":
            h_, w_ = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            fl = flare_sprite(min(h_, w_) // 2 - 1)
            glow = lit * 1.2 + (blur * 80)[..., None] * GLOW
            if c["area"] > 250:
                blit(glow, c["cy"] - sl[0].start, c["cx"] - sl[1].start, fl, WHITE if i == morse_i else GOLD, 140)
            g = B.image(nm + "g", additive(glow), cx, cy, blending="additive", depth=DEPTH[k], alpha=0.0)
            if i == morse_i:
                data["morse"] = dict(layer=g)
            else:
                data["sparks"].append(dict(g=g, f=int(rng.integers(2, 6)), ph=float(rng.random()), y=c["cy"], z=z))
        elif k == "heart":
            glow = lit * 0.8 + (blur * 90)[..., None] * GLOW
            g = B.image(nm + "g", additive(glow), cx, cy, blending="additive", depth=DEPTH[k], alpha=0.0)
            data["hearts"].append(dict(n=nm, g=g, f=int(rng.integers(5, 8)), ph=float(rng.random()), y=c["cy"], z=z))
        else:
            glow = lit * 0.7 + (blur * 70)[..., None] * GLOW
            g = B.image(nm + "g", additive(glow), cx, cy, blending="additive", depth=DEPTH[k], alpha=0.0)
            h_, w_ = c["sl"][0].stop - c["sl"][0].start, c["sl"][1].stop - c["sl"][1].start
            data["signs"].append(dict(g=g, gem=bool(c["area"] / (h_ * w_) > 0.6), y=c["cy"], z=z))

    # morse
    units = []
    for word in MORSE_TEXT.split(" "):
        for li, ch in enumerate(word):
            for si, sym in enumerate(MORSE[ch]):
                units += [1] * (1 if sym == "." else 3)
                if si < len(MORSE[ch]) - 1:
                    units += [0]
            if li < len(word) - 1:
                units += [0] * 3
        units += [0] * 7
    data["morse"].update(units=units, unit=T / 2 / len(units))

    # constelaciones: un halo oscuro + una capa por letra
    data["allMsgs"] = []
    for mid, (lines, hgt, cy, t0) in MESSAGES.items():
        gl = glyph_strokes(lines, hgt, cy, W)
        xs = [q[0] for g in gl for s in g for q in s]
        ys = [q[1] for g in gl for s in g for q in s]
        hw, hh = (max(xs) - min(xs)) * 0.62 + 60, (max(ys) - min(ys)) * 0.85 + 80
        q = 4  # el halo se guarda a 1/4 y se escala
        Y, X = np.mgrid[0:int(hh * 3 / q), 0:int(hw * 3 / q)].astype(np.float32)
        e = ((X * q - hw * 1.5) / hw) ** 2 + ((Y * q - hh * 1.5) / hh) ** 2
        halo = np.exp(-e * 1.6) * 0.3
        halo_rgba = np.concatenate([np.zeros(halo.shape + (3,)), (halo * 255)[..., None]], -1)
        hn = B.image(f"halo_{mid}", halo_rgba, W / 2, (min(ys) + max(ys)) / 2, depth=DEPTH["glyph"] * 0.5, alpha=0.0, scale=q)
        names = []
        for gi, g in enumerate(gl):
            rgba_g, gx, gy = render_glyph(g)
            names.append(B.image(f"g_{mid}_{gi}", rgba_g, gx, gy, blending="additive", depth=DEPTH["glyph"], alpha=0.0))
        data["allMsgs"].append(dict(id=mid, t0=t0, halo=hn, glyphs=names))
    data["msgs"], data["annivMsgs"] = NORMAL, ANNIV

    # cometa: cabeza + estela
    head = (gauss_sprite(4.5) * 230)[..., None] * WHITE
    fl = np.pad(flare_sprite(16), (head.shape[0] - 33) // 2) if head.shape[0] > 33 else flare_sprite(16)
    hs = max(head.shape[0], fl.shape[0])
    hc = np.zeros((hs, hs, 3), np.float32)
    o1, o2 = (hs - head.shape[0]) // 2, (hs - fl.shape[0]) // 2
    hc[o1:o1 + head.shape[0], o1:o1 + head.shape[0]] += head
    hc[o2:o2 + fl.shape[0], o2:o2 + fl.shape[0]] += (fl * 150)[..., None] * WHITE
    data["comet"].append(B.image("comet0", additive(hc), -100, -100, blending="additive", alpha=0.0))
    tail = additive((gauss_sprite(2.6) * 170)[..., None] * GOLD)
    for j in range(1, 12):
        data["comet"].append(B.image(f"comet{j}", tail, -100, -100, blending="additive", alpha=0.0))
    longs = sorted(range(len(paths)), key=lambda j: -paths[j]["length"])[:12]
    for j in longs:
        p = paths[j]
        step = max(1, int(len(p["path"]) / (p["length"] / 6)))
        pts = p["path"][::step]
        data["paths"].append([round(v, 1) for yx in pts for v in (float(yx[1]), float(H - yx[0]))])
    order = rng.permutation(len(longs))
    for n in range(8):
        j = int(order[n % len(order)])
        data["comets"].append(dict(t0=0.8 + n * 3.75, p=j, rev=bool(rng.random() < 0.5),
                                   dur=float(np.clip(paths[longs[j]]["length"] / 360, 1.1, 3.4))))

    # noche
    night = np.zeros((8, 8, 4))
    night[..., 3] = 255
    data["night"] = B.image("night", night, W / 2, H / 2, alpha=0.0, scale=max(W, H) / 8 * 1.2)

    # corazones al tocar + destello
    hs_ = heart_shape(72)
    hglow = nd.gaussian_filter(hs_, 5)
    heart_rgb = (hs_ * 210)[..., None] * GOLD + (hglow * 160)[..., None] * GLOW
    heart_rgba = additive(np.pad(heart_rgb, ((12, 12), (12, 12), (0, 0))))
    for j in range(16):
        data["taps"].append(B.image(f"tap{j}", heart_rgba, -200, -200, blending="additive", alpha=0.0))
    flash = (flare_sprite(60) * 200)[..., None] * WHITE + (np.pad(gauss_sprite(14), 60 - gauss_sprite(14).shape[0] // 2) * 120)[..., None] * GLOW
    for j in range(3):
        data["flashes"].append(B.image(f"flash{j}", additive(flash), -200, -200, blending="additive", alpha=0.0))

    data["layers"] = [n for n in B.layers if n != "base"]

    # partículas: polvo de estrellas
    mote = additive((gauss_sprite(9) * 255)[..., None] * np.array([1, 1, 1], np.float32))
    write_tex(os.path.join(OUT, "materials", "az", "mote.tex"), np.clip(mote, 0, 255).astype(np.uint8))
    json.dump({"passes": [{"shader": "particle", "blending": "additive", "cullmode": "nocull",
                           "depthtest": "disabled", "depthwrite": "disabled", "textures": ["az/mote"]}]},
              open(os.path.join(OUT, "materials", "az", "mote.json"), "w"), indent=1)
    os.makedirs(os.path.join(OUT, "particles"))
    particle = {
        "emitter": [{"id": 1, "name": "sphererandom", "origin": f"{W / 2} {H / 2} 0",
                     "distancemax": 1300, "distancemin": 0, "directions": "0.5 1 0", "rate": 9}],
        "initializer": [
            {"id": 2, "name": "lifetimerandom", "min": 5, "max": 10},
            {"id": 3, "name": "sizerandom", "min": 5, "max": 16},
            {"id": 4, "name": "velocityrandom", "min": "-6 6 0", "max": "6 26 0"},
            {"id": 5, "name": "colorrandom", "min": "235 160 110", "max": "255 220 180"},
        ],
        "operator": [
            {"id": 6, "name": "movement", "gravity": "0 0 0"},
            {"id": 7, "name": "alphafade", "fadeintime": 0.3, "fadeouttime": 0.5},
            {"id": 8, "name": "oscillatealpha", "frequencymin": 0.2, "frequencymax": 0.9, "scalemin": 0.3, "scalemax": 1,
             "phasemin": 0, "phasemax": 1},
            {"id": 9, "name": "oscillateposition", "frequencymin": 0.1, "frequencymax": 0.5, "scalemin": 6, "scalemax": 18,
             "mask": "1 0 0", "phasemin": 0, "phasemax": 1},
        ],
        "renderer": [{"id": 10, "name": "sprite"}],
        "material": "materials/az/mote.json",
        "maxcount": 120,
        "starttime": 12,
    }
    json.dump(particle, open(os.path.join(OUT, "particles", "polvo.json"), "w"), indent=1)
    B.nid += 1
    # justo después de la base para quedar detrás de los elementos
    B.objects.insert(1, {"id": B.nid, "name": "polvo", "particle": "particles/polvo.json",
                         "origin": "0.00000 0.00000 0.00000", "angles": "0.00000 0.00000 0.00000",
                         "scale": "1.00000 1.00000 1.00000", "parallaxDepth": "0.30000 0.30000", "visible": True,
                         "locktransforms": False})

    script = open(os.path.join(HERE, "director.js"), encoding="utf8").read()
    script = script.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    B.objects[0]["visible"]["script"] = script

    scene = {
        "camera": {"center": "0.00000 0.00000 -1.00000", "eye": "0.00000 0.00000 0.00000", "up": "0.00000 1.00000 0.00000"},
        "general": {
            "ambientcolor": "0.30000 0.30000 0.30000", "bloom": False, "camerafade": True,
            "cameraparallax": True, "cameraparallaxamount": 0.6, "cameraparallaxdelay": 0.12,
            "cameraparallaxmouseinfluence": 0.4, "camerapreview": True, "camerashake": False,
            "clearcolor": "0.37000 0.10000 0.07000", "clearenabled": True, "farz": 10000.0, "fov": 50.0,
            "hdr": False, "nearz": 0.01, "orthogonalprojection": {"width": W, "height": H},
            "skylightcolor": "0.30000 0.30000 0.30000", "zoom": 1.0,
        },
        "objects": B.objects,
    }
    json.dump(scene, open(os.path.join(OUT, "scene.json"), "w", encoding="utf8"), indent=1, ensure_ascii=False)

    project = {
        "file": "scene.json", "preview": "preview.jpg", "title": "Amor Zodiacal v3 (interactivo)",
        "description": "Géminis y Capricornio. Toca la pantalla, inclina el teléfono. Arte original de mi esposa.",
        "type": "scene", "visibility": "private", "tags": ["Abstract"], "contentrating": "Everyone",
        "general": {"properties": {
            "schemecolor": {"order": 0, "text": "ui_browse_properties_scheme_color", "type": "color", "value": "0.62 0.16 0.12"},
            "intensidad": {"order": 1, "text": "Intensidad del brillo", "type": "slider", "value": 1.0,
                           "min": 0.2, "max": 1.6, "step": 0.1, "precision": 1, "fraction": True},
            "mensajes": {"order": 2, "text": "Mensajes en las estrellas", "type": "bool", "value": True},
        }},
    }
    json.dump(project, open(os.path.join(OUT, "project.json"), "w", encoding="utf8"), indent=1, ensure_ascii=False)
    prev = Image.open(os.path.join(ROOT, "build", "preview", "t15.png")).convert("RGB")
    prev.resize((540, 1170)).save(os.path.join(OUT, "preview.jpg"), quality=88)
    n_img = sum(1 for o in B.objects if "image" in o)
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs)
    print(f"capas: {n_img} imágenes + 1 partículas; tamaño: {size / 1e6:.1f} MB; script: {len(script) / 1e3:.0f} KB")

    if "--install" in sys.argv:
        dst = os.path.join(WE, "amor_zodiacal_v3")
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(OUT, dst)
        print("instalado en", dst)


if __name__ == "__main__":
    main()
