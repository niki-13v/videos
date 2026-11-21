"""Parallel frame renderer: each CPU core draws and encodes a slice, then slices are joined."""
import multiprocessing as mp
import os
import subprocess
import tempfile

import cairo
import soundfile as sf

FPS = 30
_JOB = {}


def _worker(args):
    k, a, b, path = args
    draw, W, H = _JOB["draw"], _JOB["W"], _JOB["H"]
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-g", "60",
         "-threads", "1", path],
        stdin=subprocess.PIPE,
    )
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    for i in range(a, b):
        cr = cairo.Context(surf)
        draw(cr, i / FPS)
        surf.flush()
        ff.stdin.write(bytes(surf.get_data()))
        if k == 0 and (i - a) % 600 == 0:
            print(f"    frame {i - a}/{b - a} (slice 1 of {_JOB['n']})", flush=True)
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg slice failed")
    return path


def render(draw, W, H, total, wav, sr, out, workers=None):
    """draw(cr, t) paints one frame. wav is mono float audio at sr."""
    workers = workers or max(1, os.cpu_count() or 1)
    n = int(total * FPS)
    with tempfile.TemporaryDirectory() as td:
        step = -(-n // workers)
        jobs = [(k, k * step, min(n, (k + 1) * step), os.path.join(td, f"s{k:02d}.mp4")) for k in range(workers) if k * step < n]
        _JOB.update(draw=draw, W=W, H=H, n=len(jobs))
        ctx = mp.get_context("fork")
        with ctx.Pool(len(jobs)) as pool:
            parts = pool.map(_worker, jobs)
        lst = os.path.join(td, "list.txt")
        with open(lst, "w") as f:
            f.writelines(f"file '{p}'\n" for p in parts)
        wav_path = os.path.join(td, "a.wav")
        sf.write(wav_path, wav, sr)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav_path,
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out],
            check=True,
        )
