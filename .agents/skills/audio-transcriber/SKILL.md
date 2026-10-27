---
name: audio-transcriber
description: Extract audio streams from YouTube or local media and transcribe with local openai/whisper-large-v3-turbo. Use when YouTube transcripts are missing, degraded, or for offline local speech-to-text.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# Audio Transcriber (Whisper Large V3 Turbo)

Extract voice/audio from YouTube videos or local video files and generate high-accuracy word/segment transcripts using the local `openai/whisper-large-v3-turbo` model.

## Features
- **Voice/Audio Extraction:** Downloads the cleanest audio track from YouTube using `yt-dlp` and resamples to 16kHz mono WAV using `ffmpeg`.
- **Local Whisper Engine:** Runs `openai/whisper-large-v3-turbo` with `int8` quantization for fast CPU execution and low memory consumption.
- **Timestamp Synchronization:** Generates snippet-level timestamps (`start`, `duration`, `text`) fully compatible with the downstream hypothesis miner and knowledge database.

## Usage

### 1. Extract Audio from YouTube Video
```bash
uv run .agents/skills/audio-transcriber/scripts/extract_audio.py "https://www.youtube.com/watch?v=zU0i9rBbEkI"
```
*Saves to `data/audio/<video_id>.wav` (16kHz mono).*

### 2. Transcribe Audio File with Whisper Large V3 Turbo
```bash
uv run .agents/skills/audio-transcriber/scripts/transcribe_whisper.py "data/audio/zU0i9rBbEkI.wav" --video-id "zU0i9rBbEkI" --title "AI Trading Lessons" --ingest-db
```
*Outputs:*
- `data/transcripts/<video_id>.json`: Timed snippets array.
- `data/transcripts/<video_id>.txt`: Formatted reading transcript.
- Automatically indexes chunks into Chroma and records into `knowledge.db` if `--ingest-db` is passed.

### 3. All-in-One Audio Download & Transcribe
You can pipe extraction directly to transcription:
```bash
AUDIO_FILE=$(uv run .agents/skills/audio-transcriber/scripts/extract_audio.py "<VIDEO_URL>" | grep "Path:" | awk '{print $2}')
uv run .agents/skills/audio-transcriber/scripts/transcribe_whisper.py "$AUDIO_FILE" --ingest-db
```

## References
See [references/model_guide.md](references/model_guide.md) for CPU/GPU benchmarks, VRAM requirements, and quantization flags.
