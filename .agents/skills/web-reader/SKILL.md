---
name: web-reader
description: Render dynamic web pages, extract article text, capture screenshots, and inspect embedded videos, media streams, and captions using Playwright Chromium automation. Use when reading websites, SPAs, or extracting media from web pages.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# Web Reader (Playwright)

Automates headless Chromium browsing to extract clean reader-friendly content, render dynamic SPAs, take screenshots, and detect video/audio players and caption tracks.

## Capabilities
1. **Dynamic Page Extraction:** Renders JavaScript, bypasses static limits, and strips ads/scripts to yield clean markdown.
2. **Media & Caption Inspection:** Detects HTML5 `<video>` tags, `<track>` subtitle files, iframe embeds (YouTube, Vimeo, Rumble), and network `.m3u8` / `.vtt` streams.
3. **Visual Snapshots:** Saves full-page screenshots for layout verification.

## Usage

### 1. Read Any Web Page
```bash
uv run .agents/skills/web-reader/scripts/read_page.py "https://qullamaggie.com"
```

### 2. Inspect a Page for Embedded Videos and Captions
```bash
uv run .agents/skills/web-reader/scripts/inspect_video.py "https://qullamaggie.com"
```

### 3. Capture Full-Page Screenshot
```bash
uv run .agents/skills/web-reader/scripts/read_page.py "https://qullamaggie.com" --screenshot data/screenshots/qullamaggie.png
```

## References
See [references/playwright_guide.md](references/playwright_guide.md) for timeout configurations and CSS selector scoping.
