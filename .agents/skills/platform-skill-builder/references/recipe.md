# Recipe reference (`config/sites/<name>.yaml`)

One file per site; its stem is the **platform name** (letters, digits, dashes; 2-25 chars; starts with a letter). Content ids become `<name>:<native id>`. Having the file makes the platform known to ids, schema validation, `finsocnet explore add` dispatch and the standard CLI.

## Top level

| Key | Meaning |
|---|---|
| `name`, `title`, `base_url` | required (title is shown in sources) |
| `mode` | `http` (plain HTML), `browser` (agent browser, for JS sites / bot walls / sessions), `api` (JSON), `feed` (RSS/Atom for lists; `fetch` loads the page over HTTP) |
| `requires_session` | true when pages need the user's login (then `session_cookies`, `probe_url` are written to platforms.yaml; never ask for a password) |
| `source_kind` | `site` (default), `blog`, `forum`, `community`, `channel`, … shown in source ids |
| `content_type` | `article` (default), `post`, `thread`, `question`, `page`, … (content_record enum) |
| `language` | BCP-47 if the whole site is in one language, else leave out (the translator decides per content) |
| `id.from_url` | regex with ONE group that extracts the native id from an item URL; without it a hash of host+path+query is used |
| `budget` | `{per_minute, per_hour, per_day, min_delay_ms, max_delay_ms}` written to budgets.yaml (default for unknown platforms: 20/min); copy `crawl-delay` from robots.txt |
| `dispatch` | `[{pattern, action: fetch\|list\|profile}]`; `finsocnet explore add <url>` routes matching URLs to this skill. A catch-all for the domain (action `default_action`, default `list`) is added automatically |
| `refresh_hours` | how often an active source is re-crawled (default 168) |

## Operations (all optional, define what the site supports)

- `search: {url, items, fields}`; `{query}` in the URL is URL-encoded.
- `list: {url, items, fields, next}`; `{source}` is the board/tag/section the user passes, `{cursor}` the paging token; `next` is a selector (html) or path (api) of the next page. In `feed` mode only `url` is needed.
- `profile: {url, fields: {name, bio, avatar, followers}}`; `{target}` is the handle. The avatar is downloaded by `profile --ingest`.
- `fetch: {title, author, date, body, comments}`: `body` is required in html modes (selector of the element holding the text); `comments: {items, author, text}`; in `api` mode all are paths and `url` may use `{id}`.

## Field expressions

HTML: `css` = text of the first match · `css@attr` = attribute · `@href` = attribute of the item node itself · `a|b` = first alternative that yields something. URLs are made absolute. `title` selects the `<title>` element, handy when headings are ambiguous.
JSON: dotted path (`data.posts.0.title`, `user.name`).

## Cheat sheet

- Item lists: pick the *smallest* element that repeats once per item (the probe prints candidates).
- Date: prefer `time@datetime`, `meta[property='article:published_time']@content`.
- Pagination: `a[rel=next]@href` or `.pagination .next a@href`.
- A fetched body that is mostly navigation: narrow `body` (`article`, `main .content`, `div.entry-content`).
- JavaScript pages: `mode: browser`; the first request may hit a bot check (exit 3) → solve once in the agent browser.
- Examples: `examples/blog-feed.yaml` (feed + page), `examples/forum-api.yaml` (JSON API).
