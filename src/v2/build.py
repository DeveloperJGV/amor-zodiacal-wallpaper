"""Construye releases/v2: renderiza en paralelo y codifica a MP4 (H.264 y HEVC).

Uso: python src/v2/build.py [workers]
"""
import os, subprocess, sys, time
from multiprocessing import Process

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import ROOT, FPS, N  # noqa: E402

BUILD = os.path.join(ROOT, "build", "v2")
OUT = os.path.join(ROOT, "releases", "v2")


def worker(a, b, path):
    from render import Scene
    sc = Scene()
    W, H = sc.W, sc.H
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "12",
         "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for n in range(a, b):
        ff.stdin.write(sc.frame(n).tobytes())
    ff.stdin.close()
    ff.wait()


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    step = -(-N // workers)
    parts, procs = [], []
    for i in range(workers):
        a, b = i * step, min((i + 1) * step, N)
        p = os.path.join(BUILD, f"part{i:02d}.mp4")
        parts.append(p)
        procs.append(Process(target=worker, args=(a, b, p)))
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    print(f"render: {time.time() - t0:.0f}s")
    lst = os.path.join(BUILD, "parts.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    master = os.path.join(BUILD, "master.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", master], check=True)
    common = ["-an", "-movflags", "+faststart", "-r", str(FPS)]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", master, "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                    "-profile:v", "high", "-pix_fmt", "yuv420p", *common, os.path.join(OUT, "amor_zodiacal_v2.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", master, "-c:v", "libx265", "-preset", "slow", "-crf", "20",
                    "-tag:v", "hvc1", "-pix_fmt", "yuv420p", "-x265-params", "log-level=error", *common,
                    os.path.join(OUT, "amor_zodiacal_v2_hevc.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-t", "10", "-i", master, "-vf",
                    "fps=12,scale=240:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse",
                    os.path.join(OUT, "preview.gif")], check=True)
    print(f"listo en {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
