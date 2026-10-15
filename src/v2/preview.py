"""Renderiza cuadros sueltos para revisar: python preview.py out_dir t1 t2 ... (segundos)."""
import sys, os
from PIL import Image
from render import Scene, FPS
sc = Scene()
os.makedirs(sys.argv[1], exist_ok=True)
for ts in sys.argv[2:]:
    Image.fromarray(sc.frame(int(float(ts) * FPS))).save(os.path.join(sys.argv[1], f"t{ts}.png"))
