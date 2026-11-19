# Sleepy Forest Stories: automatic bedtime-story videos

Makes a complete, original bedtime-story video for kids, three times a week, for free.

**Pipeline:** Gemini writes the story → free AI draws each scene → Kokoro narrates →
an original lullaby is generated → ffmpeg builds a 1080p storybook video with slow
camera moves → thumbnail, captions and title/description are made.

## Your part (about 5 minutes per video)

1. GitHub emails you when a new **Release** appears (Watch this repo → Custom → Releases).
2. Open the release on your phone and watch the video (2x speed is fine).
3. Download `video.mp4` and `thumbnail.jpg`.
4. YouTube Studio app → upload → copy the title/description/tags from `UPLOAD.txt`.
5. Choose **"Yes, it's made for kids"** and publish (or schedule).

Bad video? Just skip it. Want one now? Actions tab → *Make bedtime story* → **Run workflow**.

## Setup (once)

Settings → Secrets and variables → Actions → New repository secret:

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | free key from https://aistudio.google.com/apikey |
| `POLLINATIONS_TOKEN` | optional, only if Pollinations starts requiring one |

## Changing things

Everything is in `config.yaml`: characters, art style, themes, voice, length,
image provider. Change the schedule in `.github/workflows/make-video.yml`.

## Run locally

```bash
pip install -r requirements.txt   # also needs ffmpeg
GEMINI_API_KEY=... python make_video.py
python make_video.py --story some_story.json --images placeholder   # offline test
```
