# Bramble & Friends: automatic toddler learning videos

Free, fully automatic. Every day GitHub makes one ~2.5 min episode (colors, animals,
shapes, counting, fruits in rotation) + 2 Shorts + thumbnail + title/description/tags.
Every Sunday it joins recent episodes into a 30+ minute compilation.

Everything is drawn and animated in code (`anim/`), voiced with free Kokoro TTS,
with public-domain nursery tunes and original sound effects. No API keys needed.

## Uploading (about 5 min a day)
1. Open the newest Release on GitHub.
2. Download the files.
3. YouTube Studio → upload → paste from `UPLOAD.txt` → "Made for kids: Yes".

## Make one now
Actions → Make episode → Run workflow (optionally pick a topic).

## Local
```bash
pip install -r requirements.txt   # needs ffmpeg + cairo
python make_episode.py --topic colors
```
