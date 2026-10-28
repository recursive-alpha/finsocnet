# Where a person can be (check what fits their profession)

| Kind | Places | How to look |
|---|---|---|
| website | personal site, company/fund/university page, speaker bio, "about" page | channel About links; `web_search.py search "\"<name>\" official site"`; `web.py fetch` |
| social | X, LinkedIn, Instagram, Facebook, TikTok, Threads, Bluesky, Mastodon, Reddit, Telegram, Discord, StockTwits, TradingView | each platform skill: `search "<name>"`, `profile <handle>`; LinkedIn/Facebook/Instagram need sessions: list as `not_possible` without one |
| video / audio | YouTube channels (main, clips, second channel), podcasts, Spotify/Apple shows, interview series | `youtube.py search "<name>" --type channel`, `podcast.py search "<name>"` |
| newsletter | Substack, beehiiv, Medium, Ghost, Seeking Alpha author page, own domain | `substack.py profile`, `rss.py discover <site>`, `medium.py profile` |
| code | GitHub, GitLab, Pine scripts on TradingView | `github.py profile <handle>` |
| paper / scholar | OpenAlex, Semantic Scholar, SSRN author page, NBER, RePEc, ORCID, Google Scholar | `research.py profile "<name>"`; web-searcher for the other pages; keep ids in `external_ids` |
| wiki | Wikipedia, Wikidata | web-searcher `"<name>" wikipedia`; the Wikipedia article often lists official site and handles |
| course / book / store | course platforms, book pages (Amazon, publisher), shop | the official site; `annas.py search` only to identify a book, not to download |

Executives and founders: company "leadership" page, shareholder letters, SEC filings (`sec.py`), conference talks. Professors and researchers: department page, CV, working-paper series. Central bankers and regulators: institution page, speeches. Traders: prop firm or fund page, course site, interview appearances.
