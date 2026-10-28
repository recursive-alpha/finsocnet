"""Discord: user mode through the agent browser (reads the client's own REST responses; the script never sends requests with the
token) and bot mode with the official API (docs/spec/05 §3.1).

ToS: automating a user account violates Discord's terms ("self-bots") and can get the account banned. Use a secondary account,
keep budgets low, read only (SPEC §9 Q2). Bot mode is only for servers where the user added the bot."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from finsocnet.adapters import _browser
from finsocnet.core import browser, http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, save_raw
from finsocnet.core.segments import refs

API = "https://discord.com/api/v10"
MSG_PATTERN = r"/api/v\d+/channels/\d+/messages(\?|$)"
SNOWFLAKE_EPOCH = 1420070400000


def snowflake_day(sf: str) -> str:
    return datetime.fromtimestamp(((int(sf) >> 22) + SNOWFLAKE_EPOCH) / 1000, timezone.utc).strftime("%Y-%m-%d")


def parse_link(ref: str) -> tuple[str | None, str, str | None]:
    """`https://discord.com/channels/<guild>/<channel>[/<message>]` or a bare channel id -> (guild, channel, message)."""
    m = re.search(r"channels/(@me|\d+)/(\d+)(?:/(\d+))?", ref)
    if m:
        return m.group(1), m.group(2), m.group(3)
    if re.fullmatch(r"\d{15,22}", ref.strip()):
        return None, ref.strip(), None
    raise CliError("USAGE", f"cannot read a Discord channel from {ref!r}", "use https://discord.com/channels/<guild>/<channel>[/<message>]")


def message_text(m: dict[str, Any]) -> str:
    parts = [m.get("content") or ""]
    for e in m.get("embeds", []):
        parts += [x for x in (e.get("title"), e.get("description")) if x]
    return "\n".join(p for p in parts if p).strip()


def build_record(channel_id: str, day: str, messages: list[dict[str, Any]], guild: str | None, channel_name: str | None, raw_path: str | None) -> dict[str, Any]:
    msgs = sorted({m["id"]: m for m in messages if snowflake_day(m["id"]) == day}.values(), key=lambda m: int(m["id"]))
    segs, media = [], []
    for m in msgs:
        text = message_text(m)
        att = [a["url"] for a in m.get("attachments", []) if a.get("url")]
        media += [{"kind": "attachment", "url": u} for u in att]
        if not text and not att:
            continue
        a = m.get("author") or {}
        loc: dict[str, Any] = {"message_id": m["id"]}
        if (m.get("message_reference") or {}).get("message_id"):
            loc["reply_to"] = m["message_reference"]["message_id"]
        segs.append({"seq": len(segs), "kind": "message", "locator": loc, "author": {"handle": a.get("username"), "display_name": a.get("global_name"), "platform_user_id": a.get("id")}, "text": text or "(attachment)"})
    r = refs("\n".join(s["text"] for s in segs))
    return content_record(f"discord:{channel_id}:{day}", "discord", "chat_window", segs or [{"seq": 0, "kind": "message", "locator": {}, "text": "(no messages)"}],
                          url=f"https://discord.com/channels/{guild or '@me'}/{channel_id}", title=f"#{channel_name or channel_id} {day}", published_at=f"{day}T00:00:00Z", links=r["links"], mentions=r["mentions"], media=media,
                          raw_path=raw_path, fetch_method="client_rest_capture", extra={"guild_id": guild, "channel_id": channel_id, "private_source": True, "message_count": len(msgs)},
                          source={"id": f"discord:channel:{channel_id}", "kind": "channel_chat", "title": channel_name or channel_id, "requires_session": True})


class Discord(PlatformAdapter):
    platform = "discord"
    requires_session = True
    capabilities = frozenset({"list", "fetch", "search"})
    opts = {"fetch": [(("--day",), {}), (("--mode",), {"default": "user", "choices": ["user", "bot"]}), (("--max-messages",), {"type": int, "default": 2000})],
            "list": [(("--mode",), {"default": "user", "choices": ["user", "bot"]})], "search": [(("--guild",), {"required": True})]}

    def _bot_get(self, path: str, **params: Any) -> Any:
        tok = os.getenv("DISCORD_BOT_TOKEN")
        if not tok:
            raise CliError("USAGE", "DISCORD_BOT_TOKEN is not set", "bot mode only works for servers where you added the bot")
        return http.get_json(f"{API}{path}", platform="discord", params=params or None, headers={"Authorization": f"Bot {tok}"})

    def fetch(self, item, *, day=None, mode="user", max_messages=2000, **_):
        guild, channel, message = parse_link(item)
        day = day or (snowflake_day(message) if message else datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        if mode == "bot":
            msgs, before = [], None
            while len(msgs) < max_messages:
                batch = self._bot_get(f"/channels/{channel}/messages", limit=100, **({"before": before} if before else {}))
                if not batch:
                    break
                msgs += batch
                before = batch[-1]["id"]
                if snowflake_day(before) < day:
                    break
            name = None
        else:
            url = f"https://discord.com/channels/{guild or '@me'}/{channel}" + (f"/{message}" if message else "")
            _u, bodies = _browser.capture("discord", url, MSG_PATTERN, scrolls=max(3, max_messages // 50), until=lambda b: any(snowflake_day(m["id"]) < day for body in b if isinstance(body, list) for m in body))
            msgs = [m for body in bodies if isinstance(body, list) for m in body if isinstance(m, dict) and "id" in m]
            name = None
        if not msgs:
            raise CliError("NOT_FOUND", f"no messages captured for channel {channel} (not visible to this account, or the client did not load them)")
        return build_record(channel, day, msgs, guild, name, save_raw("discord", f"{channel}_{day}", msgs))

    def list(self, source, *, limit=50, cursor=None, since=None, mode="user", **_):
        if source == "servers":
            _f, html = _browser.load_html("discord", "https://discord.com/channels/@me", wait="networkidle")
            from lxml import html as lhtml
            names = {a.get("data-list-item-id", "") or a.get("href", ""): (a.get("aria-label") or "").strip() for a in lhtml.fromstring(html).xpath("//*[@data-list-item-id and contains(@data-list-item-id,'guildsnav___')]")}
            items = [item_ref(f"https://discord.com/channels/{k.rsplit('_', 1)[-1]}", f"discord:server:{k.rsplit('_', 1)[-1]}", "server", n, None, None, None) for k, n in names.items() if k.rsplit("_", 1)[-1].isdigit()]
            return list_result(items[:limit], None, {"id": "discord:servers"})
        if mode == "bot" and source.isdigit():
            chans = self._bot_get(f"/guilds/{source}/channels")
            items = [item_ref(f"https://discord.com/channels/{source}/{c['id']}", f"discord:channel:{c['id']}", "channel", c.get("name"), None, None, None) for c in chans if c.get("type") in (0, 5, 15)]
            return list_result(items[:limit], None, {"id": f"discord:server:{source}"})
        raise CliError("UNSUPPORTED", "use `list servers`, or `list <guild_id> --mode bot`", "in user mode open the server in the agent browser and fetch channel links directly")

    def search(self, query, *, limit=20, since=None, guild=None, **_):
        raise CliError("UNSUPPORTED", "Discord in-app search needs UI automation that is not verified", "fetch the channel day windows and use `kb content search` on the stored messages")
