# Dispatch rules: target → skill

Check rows top to bottom; the first match wins. Script paths are `.agents/skills/<skill>/scripts/<script>`.

| Target pattern | Skill | Script · subcommand |
|---|---|---|
| `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | youtube-extractor | `youtube.py fetch` |
| `youtube.com/@…`, `youtube.com/channel/UC…`, `youtube.com/c/…` | youtube-extractor | `youtube.py profile`, then `list --tab all` |
| `x.com/<h>/status/<id>`, `twitter.com/<h>/status/<id>` | x-explorer | `x.py fetch` |
| `x.com/<h>`, `twitter.com/<h>`, `@handle` with platform x | x-explorer | `x.py profile`, `list` |
| `reddit.com/r/<s>/comments/<id>`, `redd.it/<id>` | reddit-explorer | `reddit.py fetch` |
| `reddit.com/r/<s>`, `reddit.com/user/<u>`, `u/<u>` | reddit-explorer | `reddit.py profile`, `list` |
| `medium.com/…-<12 hex>`, `<pub>.medium.com/…` | medium-explorer | `medium.py fetch` |
| `medium.com/@<h>`, `medium.com/tag/<t>` | medium-explorer | `medium.py profile`, `list` |
| `<x>.substack.com/p/…`, custom domain page with Substack markers | substack-explorer | `substack.py fetch` |
| `<x>.substack.com`, `substack.com/@<h>` | substack-explorer | `substack.py profile`, `list` |
| `podcasts.apple.com/…`, RSS feed with `<enclosure>` audio | podcast-explorer | `podcast.py profile`, `list` / `fetch` |
| `discord.com/channels/<g>/<c>[/<m>]`, `discord.gg/<invite>` | discord-explorer | `discord.py fetch` / `list` |
| `t.me/<c>`, `t.me/s/<c>`, `t.me/<c>/<id>` | telegram-explorer | `telegram.py list` / `fetch` |
| `stackoverflow.com/questions/<id>`, `<site>.stackexchange.com/questions/<id>` | stackexchange-explorer | `stackexchange.py fetch --site …` |
| host listed in `config/forums.yaml`, or a page with forum engine markers | forum-explorer | `forum.py fetch` / `list` |
| `tradingview.com/chart/…` (idea), `tradingview.com/script/…` | tradingview-explorer | `tradingview.py fetch` |
| `tradingview.com/u/<user>` | tradingview-explorer | `tradingview.py profile`, `list` |
| `facebook.com/groups/…`, `facebook.com/<page>`, `fb.com/…`, `fb.watch/…` | facebook-explorer | `facebook.py …` |
| `sec.gov/…`, `CIK …` | sec-edgar-explorer | `sec.py …` |
| `arxiv.org/abs/…`, `arxiv.org/pdf/…` | paper-code-explorer | `papers.py fetch` |
| `ssrn.com/abstract=…`, `papers.ssrn.com/…`, `doi.org/…`, `openalex.org/…`, `nber.org/papers/…` | research-explorer | `research.py fetch` |
| `github.com/<o>/<r>` | github-explorer | `github.py fetch` / `tree` |
| `bsky.app/profile/<h>[/post/<id>]` | bluesky-explorer | `bluesky.py …` |
| `stocktwits.com/…` | stocktwits-explorer | `stocktwits.py …` |
| `tiktok.com/@<h>[/video/<id>]` | tiktok-explorer | `tiktok.py …` |
| `instagram.com/<h>`, `instagram.com/p/…`, `/reel/…` | instagram-explorer | `instagram.py …` |
| `threads.net/@<h>`, `threads.com/@<h>` | threads-explorer | `threads.py …` |
| `linkedin.com/in/<h>`, `linkedin.com/posts/…`, `linkedin.com/pulse/…` | linkedin-explorer | `linkedin.py …` |
| `seekingalpha.com/article/…`, `seekingalpha.com/author/…` | seekingalpha-explorer | `seekingalpha.py …` |
| `news.ycombinator.com/item?id=…` | hackernews-explorer | `hackernews.py fetch` |
| URL ending `.pdf`, `.epub`, `.docx`, or a local path | document-reader | `document.py fetch` |
| Twitch/Vimeo/Rumble/Kick video URL | audio-transcriber + web-reader | `web.py fetch` for metadata, `transcribe.py` for speech |
| a site that custom recipes cover (`config/sites/<name>.yaml`) | `<name>-explorer` | its `list` / `fetch` (rules come from the recipe's `dispatch`) |
| any other URL | web-reader | `web.py discover`, then `fetch`; if the site deserves repeated exploration (lists, search, many pages), run `platform-skill-builder` to give it its own skill |
| `target_kind = query` | web-searcher (default) or google-searcher (when DuckDuckGo results are thin or operators like `inurl:` are needed) | `search` → enqueue results |
| `target_kind = person` | person-matcher + platform `profile` on every known alias; then web-searcher "<name> trader" to find other platforms | |
| `target_kind = book` | annas-archive-explorer | `annas.py search` → agent picks edition → `download` → document-reader |
| `target_kind = paper` | paper-code-explorer or research-explorer | `search` / `fetch --pdf` |
