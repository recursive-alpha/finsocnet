# Telegram Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://t.me/s/<channel>?before=<msg_id>` (HTML `.tgme_widget_message`)
- `https://t.me/s/<channel>?q=<query>`
- Telegram Web K DOM (browser mode)

## Verify in the Phase spike

- [ ] Telegram Web session restore from localStorage

## Change log

| Date | Change | Lesson |
|---|---|---|
