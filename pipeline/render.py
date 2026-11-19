"""Turn scene images + narration into a finished video with ffmpeg."""
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

MOVES = [
    # (zoom expression, x expression, y expression): slow storybook camera moves
    ("1+0.10*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),                 # zoom in, centre
    ("1.10-0.10*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),              # zoom out
    ("1.08", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),                       # pan right
    ("1.08", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),                   # pan left
    ("1+0.08*on/{n}", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*0.3"),                 # zoom in, upper
]


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def scene_clip(img, wav, dur, i, out, w, h, fps):
    n = int(dur * fps)
    z, x, y = (e.format(n=n) for e in MOVES[i % len(MOVES)])
    vf = (
        f"scale={w * 2}:{h * 2},"  # upscale first so the slow zoom stays smooth
        f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={fps},"
        f"fade=t=in:st=0:d=0.6,fade=t=out:st={dur - 0.6:.2f}:d=0.6,format=yuv420p"
    )
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", img, "-i", wav, "-vf", vf,
        "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", out,
    ])


def assemble(clips, music, out, music_volume):
    listfile = out + ".txt"
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    joined = out + ".joined.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", joined])
    _run([
        "ffmpeg", "-y", "-i", joined, "-i", music,
        "-filter_complex",
        f"[1:a]volume={music_volume}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,"
        "loudnorm=I=-16:TP=-1.5:LRA=11[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", out,
    ])
    os.remove(joined)
    os.remove(listfile)


def thumbnail(img_path, title, out, w=1280, h=720):
    """Big friendly title on the best scene image. Short text reads on phones."""
    img = Image.open(img_path).convert("RGB").resize((w, h), Image.LANCZOS)
    shade = Image.new("L", (w, h), 0)
    ImageDraw.Draw(shade).rectangle([0, int(h * 0.62), w, h], fill=150)
    img.paste((15, 15, 40), mask=shade.filter(ImageFilter.GaussianBlur(40)))
    words = title.split("|")[0].split(":")[0].strip()
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 78)
    except OSError:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(img)
    lines, line = [], ""
    for wd in words.split():
        if d.textlength(line + wd, font=font) > w * 0.88:
            lines.append(line.strip())
            line = ""
        line += wd + " "
    lines.append(line.strip())
    lines = lines[:2]
    y = h - 40 - len(lines) * 92
    for ln in lines:
        x = (w - d.textlength(ln, font=font)) / 2
        d.text((x, y), ln, font=font, fill=(255, 236, 170), stroke_width=6, stroke_fill=(30, 25, 60))
        y += 92
    img.save(out, quality=92)
    return out
