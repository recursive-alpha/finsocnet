# YouTube Extractor — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- yt-dlp `-J` (metadata), `--flat-playlist` on `/videos`, `/shorts`, `/streams`
- yt-dlp `ytsearch<N>:<query>`
- youtube-transcript-api list/fetch transcripts
- yt-dlp `--cookies data/sessions/cookies.txt`

## Verify in the Phase spike

- [ ] cookies.txt avoids bot check on the remote IP
- [ ] members-only video with an imported member session

## Change log

| Date | Change | Lesson |
|---|---|---|
