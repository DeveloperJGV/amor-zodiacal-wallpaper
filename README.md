# Amor Zodiacal

Wallpaper animado para Samsung S24 (Wallpaper Engine) a partir de la ilustración original
`Wallpaper001.jpeg`: Géminis y Capricornio, corazones y estrellas.

La idea central: no se le ponen efectos genéricos encima al dibujo. Se separa el dibujo en sus
piezas (estrellas, corazones, signos, caminos punteados) y se anima cada una.

## Versiones

| Versión | Tipo | Qué tiene |
|---|---|---|
| **v1** | Video, 10 s, 30 fps | Estrellas que titilan, corazones que laten, signos que respiran, ola de luz, partículas. |
| **v2** | Video, 30 s, 60 fps | Todo lo de v1, más constelaciones que se dibujan solas (J ♥ C, TE AMO, 18·10·25), cometas que recorren los caminos punteados, un secreto en morse y la zona del reloj más tenue. |
| **v3** | Scene interactiva (beta) | Igual que v2, pero en vivo: parallax al inclinar el teléfono, corazones al tocar, modo noche y sorpresa el 18 de octubre. |

### El secreto en morse
Una de las estrellas grandes, abajo a la derecha, no titila como las demás:
parpadea `- . / .- -- ---` = **TE AMO**, dos veces en cada ciclo de 30 s.

## Estructura
```
Wallpaper001.jpeg      ilustración original
src/seg.py, render.py  v1
src/v2/                v2: segment.py (análisis), glyphs.py (letras), render.py, build.py
src/v3/                v3: build_scene.py (genera el proyecto Scene), director.js, tex.py
releases/vN/           resultados listos para usar
```

## Cómo regenerar
```bash
python -m venv venv && venv/Scripts/pip install -r requirements.txt
venv/Scripts/python src/v2/segment.py            # análisis del dibujo -> build/seg_v2.pkl
venv/Scripts/python src/v2/build.py              # video v2 -> releases/v2/
venv/Scripts/python src/v3/build_scene.py --install   # proyecto Scene v3 -> Wallpaper Engine
```
