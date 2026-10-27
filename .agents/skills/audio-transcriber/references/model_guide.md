# Whisper Large V3 Turbo Reference & Hardware Guide

## Model Overview
- **Model:** `openai/whisper-large-v3-turbo` (served via `faster-whisper` CTranslate2 implementation).
- **Architecture:** 4-decoder-layer fine-tuned Whisper model achieving large-v3 accuracy at 8x the inference speed.
- **Quantization:** `int8` quantization runs on CPU with ~1.5 GB memory footprint and near-zero precision degradation.

## Hardware Profiles
- **CPU Mode (Current Workstation):**
  - Compute type: `int8`
  - Threads: Auto-tuned across available 12 CPU cores.
  - Typical RTF (Real-Time Factor): 0.15 - 0.35x (10-minute video transcribes in ~1.5 - 3 minutes on 12 CPU cores).
- **GPU Mode (CUDA / ROCm):**
  - Compute type: `float16`
  - VRAM Requirement: ~2.5 GB.

## Configuration in `.env`
```env
WHISPER_MODEL=openai/whisper-large-v3-turbo
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=int8
AUDIO_DOWNLOAD_DIR=data/audio
```
