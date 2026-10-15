"""Letras tipo constelación: cada glifo es una lista de trazos (polilíneas).

Coordenadas en una caja de alto 1 (y crece hacia abajo); el ancho es el avance del glifo.
Cada vértice se convierte en una estrella y cada segmento en una línea de constelación.
"""
import math


def _arc(cx, cy, rx, ry, a0, a1, n):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]


def _heart(n=14):
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((0.42 + x / 38, 0.45 - y / 34))
    return pts


GLYPHS = {
    "T": (0.62, [[(0, 0), (0.31, 0), (0.62, 0)], [(0.31, 0), (0.31, 0.5), (0.31, 1)]]),
    "E": (0.55, [[(0.55, 0), (0, 0), (0, 0.5), (0, 1), (0.55, 1)], [(0, 0.5), (0.42, 0.5)]]),
    "A": (0.66, [[(0, 1), (0.16, 0.55), (0.33, 0), (0.5, 0.55), (0.66, 1)], [(0.16, 0.55), (0.5, 0.55)]]),
    "M": (0.78, [[(0, 1), (0, 0), (0.39, 0.6), (0.78, 0), (0.78, 1)]]),
    "O": (0.7, [_arc(0.35, 0.5, 0.35, 0.5, -90, 270, 11)]),
    "J": (0.55, [[(0.12, 0), (0.55, 0)], [(0.42, 0), (0.42, 0.72)] + _arc(0.21, 0.72, 0.21, 0.28, 0, 160, 5)[1:]]),
    "C": (0.62, [_arc(0.36, 0.5, 0.36, 0.5, -45, -315, 9)]),
    "♥": (0.84, [_heart(12)]),
    "1": (0.36, [[(0.04, 0.22), (0.26, 0), (0.26, 0.5), (0.26, 1)]]),
    "8": (0.56, [_arc(0.28, 0.24, 0.22, 0.24, 90, 450, 8), _arc(0.28, 0.73, 0.28, 0.27, -90, 270, 9)]),
    "0": (0.56, [_arc(0.28, 0.5, 0.28, 0.5, -90, 270, 10)]),
    "2": (0.56, [[(0.02, 0.24)] + _arc(0.28, 0.27, 0.26, 0.27, 190, 370, 5)[1:] + [(0.36, 0.62), (0, 1), (0.56, 1)]]),
    "5": (0.56, [[(0.54, 0), (0.08, 0), (0.04, 0.45)] + _arc(0.26, 0.69, 0.3, 0.31, -110, 140, 7)]),
    "F": (0.5, [[(0.5, 0), (0, 0), (0, 0.5), (0, 1)], [(0, 0.5), (0.4, 0.5)]]),
    "L": (0.5, [[(0, 0), (0, 0.5), (0, 1), (0.5, 1)]]),
    "I": (0.2, [[(0.1, 0), (0.1, 0.5), (0.1, 1)]]),
    "Z": (0.56, [[(0, 0), (0.56, 0), (0.28, 0.5), (0, 1), (0.56, 1)]]),
    "N": (0.6, [[(0, 1), (0, 0), (0.6, 1), (0.6, 0)]]),
    "V": (0.62, [[(0, 0), (0.31, 1), (0.62, 0)]]),
    "R": (0.56, [[(0, 1), (0, 0), (0.34, 0), (0.52, 0.12), (0.52, 0.37), (0.34, 0.5), (0, 0.5)], [(0.26, 0.5), (0.56, 1)]]),
    "S": (0.56, [[(0.52, 0.12), (0.38, 0), (0.16, 0), (0.03, 0.13), (0.08, 0.38), (0.46, 0.6), (0.55, 0.82), (0.42, 1), (0.15, 1), (0.02, 0.88)]]),
    "·": (0.2, [[(0.1, 0.55)]]),
    " ": (0.35, []),
}


def layout(text, height, cx, cy, spacing=0.22):
    """Devuelve (trazos, estrellas) en pixeles, centrado en (cx, cy)."""
    total = sum(GLYPHS[c][0] for c in text) + spacing * (len(text) - 1)
    x = cx - total * height / 2
    y0 = cy - height / 2
    strokes = []
    for c in text:
        adv, strk = GLYPHS[c]
        for s in strk:
            pts = []
            for px, py in s:
                q = (x + px * height, y0 + py * height)
                if not pts or math.dist(pts[-1], q) > 0.06 * height:
                    pts.append(q)
            strokes.append(pts)
        x += (adv + spacing) * height
    return strokes
