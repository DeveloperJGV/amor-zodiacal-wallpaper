"""Lectura/escritura del formato .tex de Wallpaper Engine (RGBA8888, LZ4).

Estructura (deducida de los .tex de los proyectos de ejemplo):
  "TEXV0005\0" "TEXI0001\0"
  int32 formato (0 = RGBA8888), flags (2 = clampuvs),
        ancho/alto de textura (potencia de 2), ancho/alto de imagen, unk (0xFF000000)
  "TEXB0003\0" int32 n_imagenes, int32 formato_libre (-1)
  por imagen: int32 n_mipmaps; por mip: ancho, alto, lz4 (1), tamaño sin comprimir, tamaño, bytes
"""
import struct
import lz4.block
import numpy as np


def _pot(n):
    p = 1
    while p < n:
        p *= 2
    return p


def write_tex(path, rgba, clamp=True):
    """rgba: array uint8 (alto, ancho, 4)."""
    h, w = rgba.shape[:2]
    tw, th = _pot(w), _pot(h)
    canvas = np.zeros((th, tw, 4), np.uint8)
    canvas[:h, :w] = rgba
    raw = canvas.tobytes()
    comp = lz4.block.compress(raw, store_size=False)
    out = b"TEXV0005\0TEXI0001\0"
    out += struct.pack("<7I", 0, 2 if clamp else 0, tw, th, w, h, 0xFF000000)
    out += b"TEXB0003\0" + struct.pack("<iii", 1, -1, 1)
    out += struct.pack("<5i", tw, th, 1, len(raw), len(comp)) + comp
    open(path, "wb").write(out)


def read_tex(path):
    b = open(path, "rb").read()
    fmt, flags, tw, th, w, h, _ = struct.unpack("<7I", b[18:46])
    o = 46 + 9
    _, _, mips = struct.unpack("<3i", b[o:o + 12])
    o += 12
    mw, mh, is_lz4, unc, n = struct.unpack("<5i", b[o:o + 20])
    o += 20
    data = b[o:o + n]
    if is_lz4:
        data = lz4.block.decompress(data, uncompressed_size=unc)
    img = np.frombuffer(data, np.uint8).reshape(mh, mw, 4)
    return dict(fmt=fmt, flags=flags, tex=(tw, th), img=(w, h), mips=mips, pixels=img[:h, :w])


if __name__ == "__main__":
    import sys
    from PIL import Image
    t = read_tex(sys.argv[1])
    print({k: v for k, v in t.items() if k != "pixels"})
    ref = np.asarray(Image.open(sys.argv[2]).convert("RGBA"))
    print("dif vs png:", np.abs(t["pixels"].astype(int) - ref).mean())
    write_tex("_roundtrip.tex", ref)
    r = read_tex("_roundtrip.tex")
    print("roundtrip:", np.abs(r["pixels"].astype(int) - ref).mean(), r["tex"], r["img"])
