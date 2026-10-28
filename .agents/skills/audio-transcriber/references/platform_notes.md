# Audio Transcriber — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- faster-whisper WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
- yt-dlp `-x --audio-format wav`

## Verify in the Phase spike

- [ ] throughput on the remote host (minutes of audio per minute)

## Change log

| Date | Change | Lesson |
|---|---|---|
