#!/usr/bin/env python3
"""Builds docs/assets/cover.svg (and cover.png when playwright is available): `python docs/assets/build_cover.py`.

Self-contained SVG: platform glyphs are inlined from docs/assets/icons/ (simple-icons, CC0), the mark from assets/icon_transparent.svg.
"""

import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
W, H = 1800, 920

PLATFORMS = [("reddit", "#FF4500"), ("threads", "#1c1c1f"), ("x", "#111113"), ("youtube", "#FF0000"),
             ("instagram", "#E1306C"), ("facebook", "#1877F2"), ("linkedin", "#0A66C2"), ("discord", "#5865F2"),
             ("telegram", "#26A5E4"), ("medium", "#2a2a2e"), ("substack", "#FF6719"), ("github", "#2b3137"),
             ("ycombinator", "#FF6600"), ("stackexchange", "#1E5397"), ("tiktok", "#161823"), ("bluesky", "#0085FF")]
CHIPS = ["48 skills", "Knowledge Cards with citations", "Agent-judged dedup", "Keyword + semantic search", "Translate to English",
         "Any topic, any community", "Visited-item tracking", "People, rulebooks, avatars", "Reverse anything (REA)",
         "Build a skill for any site", "Session bridge, no passwords", "CLI: JSON or --ui", "Next.js web UI", "Self-improving"]


def glyph(name: str) -> str:
    svg = (HERE / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    return "".join(re.findall(r'<path[^>]*\sd="([^"]+)"', svg)) and "".join(f'<path d="{d}"/>' for d in re.findall(r'<path[^>]*\sd="([^"]+)"', svg))


def mark() -> str:
    svg = (ROOT / "assets" / "icon_transparent.svg").read_text(encoding="utf-8")
    body = re.search(r"<g transform=.*</g>", svg, re.S).group(0)
    return body


def chip(x: int, y: int, text: str) -> tuple[str, int]:
    w = int(len(text) * 11.4 + 44)
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="46" rx="23" fill="#ffffff" fill-opacity="0.06" stroke="#6ee7c8" stroke-opacity="0.45"/>'
            f'<text x="{x + w / 2}" y="{y + 30}" text-anchor="middle" class="chip">{html.escape(text)}</text></g>'), w


def build() -> str:
    o: list[str] = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="FinSocNet: AI agents read platforms like Reddit, Threads, X and YouTube, keep what they learn in one SQLite file as cited Knowledge Cards, and answer by keyword and meaning">')
    o.append('''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0B132B"/><stop offset=".5" stop-color="#16234D"/><stop offset="1" stop-color="#241B4B"/></linearGradient>
<radialGradient id="glow" cx=".62" cy=".36" r=".55"><stop offset="0" stop-color="#00F0FF" stop-opacity=".16"/><stop offset="1" stop-color="#00F0FF" stop-opacity="0"/></radialGradient>
<linearGradient id="mark-grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00F0FF"/><stop offset="45%" stop-color="#00FFA3"/><stop offset="100%" stop-color="#8B5CF6"/></linearGradient>
<linearGradient id="ai" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00F0FF"/><stop offset=".55" stop-color="#00FFA3"/><stop offset="1" stop-color="#8B5CF6"/></linearGradient>
<marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#6ee7c8"/></marker>
<style>
text{font-family:Inter,"Segoe UI","Helvetica Neue",Arial,sans-serif}
.title{font-size:104px;font-weight:800;fill:#fff;letter-spacing:-2px}
.tag{font-size:33px;fill:#c3cdea}
.hl{fill:#fff;font-weight:700}
.sub{font-size:28px;fill:#00FFA3;font-weight:600;letter-spacing:.5px}
.chip{font-size:21px;fill:#e8eeff;font-weight:500}
.cap{font-size:19px;fill:#9fb0d9;letter-spacing:1.6px;font-weight:600}
.ct{font-size:25px;font-weight:700;fill:#fff}
.cs{font-size:18px;fill:#aab8de;font-family:"DejaVu Sans Mono","SFMono-Regular",Consolas,monospace}
.flow{stroke:#6ee7c8;stroke-width:3;fill:none;stroke-dasharray:9 8;animation:dash 1.4s linear infinite}
@keyframes dash{to{stroke-dashoffset:-34}}
@media (prefers-reduced-motion:reduce){.flow{animation:none}}
</style></defs>''')
    o.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#glow)"/>')
    # title block
    o.append(f'<g transform="translate(40 70) scale(0.62)">{mark()}</g>')
    o.append('<text x="70" y="400" class="title">FinSocNet</text>')
    o.append('<text x="74" y="468" class="tag">AI agents <tspan class="hl">read the internet</tspan> for you,</text>')
    o.append('<text x="74" y="512" class="tag">keep what they learn as <tspan class="hl">cited knowledge</tspan></text>')
    o.append('<text x="74" y="556" class="tag">in one SQLite file, and <tspan class="hl">answer by meaning</tspan>.</text>')
    o.append('<text x="74" y="620" class="sub">Any topic · any language · any platform</text>')
    # platform grid
    gx0, gy0, step, r = 760, 120, 84, 33
    o.append(f'<text x="{gx0 - r}" y="{gy0 - 52}" class="cap">PLATFORMS  ·  48 SKILLS</text>')
    for i, (name, color) in enumerate(PLATFORMS):
        cx, cy = gx0 + (i % 4) * step, gy0 + (i // 4) * step
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" stroke="#ffffff" stroke-opacity=".18"/>')
        o.append(f'<g transform="translate({cx - 15} {cy - 15}) scale(1.25)" fill="#fff">{glyph(name)}</g>')
    gx1 = gx0 + 3 * step + r
    # AI node
    ax, ay = 1170, 288
    o.append(f'<text x="{ax}" y="{gy0 - 52}" text-anchor="middle" class="cap">AI HARNESS</text>')
    o.append(f'<circle cx="{ax}" cy="{ay}" r="72" fill="url(#ai)" opacity=".16"/><circle cx="{ax}" cy="{ay}" r="58" fill="#0B132B" stroke="url(#ai)" stroke-width="5"/>')
    o.append(f'<text x="{ax}" y="{ay + 12}" text-anchor="middle" style="font-size:36px;font-weight:800;fill:#fff">AI</text>')
    o.append(f'<text x="{ax}" y="{ay + 112}" text-anchor="middle" class="cs">reads · judges</text><text x="{ax}" y="{ay + 138}" text-anchor="middle" class="cs">translates · writes</text>')
    # sqlite
    sx, sy = 1385, 288
    o.append(f'<text x="{sx}" y="{gy0 - 52}" text-anchor="middle" class="cap">ONE FILE</text>')
    o.append(f'<rect x="{sx - 82}" y="{sy - 78}" width="164" height="156" rx="22" fill="#ffffff" fill-opacity="0.06" stroke="#6ee7c8" stroke-opacity=".5"/>')
    o.append(f'<g transform="translate({sx - 24} {sy - 58}) scale(2)" fill="#7dd3fc">{glyph("sqlite")}</g>')
    o.append(f'<text x="{sx}" y="{sy + 38}" text-anchor="middle" class="ct" style="font-size:21px">FTS5 + vectors</text><text x="{sx}" y="{sy + 64}" text-anchor="middle" class="cs">knowledge.db</text>')
    # outputs
    ox = 1500
    o.append(f'<text x="{ox}" y="{gy0 - 52}" class="cap">YOU GET</text>')
    cards = [("Knowledge Cards", "claims with exact quotes", 94), ("People & rulebooks", "avatars · strategies", 214), ("Search", "keyword + meaning", 334)]
    for title, sub, y in cards:
        o.append(f'<rect x="{ox}" y="{y}" width="250" height="104" rx="16" fill="#ffffff" fill-opacity="0.06" stroke="#8B5CF6" stroke-opacity=".55"/>')
        o.append(f'<text x="{ox + 18}" y="{y + 42}" class="ct">{html.escape(title)}</text><text x="{ox + 18}" y="{y + 76}" class="cs" style="font-size:15.5px">{html.escape(sub)}</text>')
    # arrows
    o.append(f'<path class="flow" d="M {gx1 + 26} {ay} H {ax - 80}" marker-end="url(#arr)"/>')
    o.append(f'<path class="flow" d="M {ax + 80} {ay} H {sx - 98}" marker-end="url(#arr)"/>')
    for y in (146, 266, 386):
        o.append(f'<path class="flow" d="M {sx + 84} {ay} C {sx + 120} {ay} {ox - 50} {y} {ox - 8} {y}" marker-end="url(#arr)"/>')
    # chips
    x, y, row = 70, 700, 0
    for text in CHIPS:
        c, w = chip(x, y, text)
        if x + w > W - 60:
            x, y = 70, y + 62
            c, w = chip(x, y, text)
        o.append(c)
        x += w + 16
    o.append(f'<text x="{W - 60}" y="{H - 30}" text-anchor="end" class="cs">Claude Code · Codex · Hermes · Pi · OMP · OpenClaw</text>')
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    svg = build()
    (HERE / "cover.svg").write_text(svg, encoding="utf-8")
    print("wrote", HERE / "cover.svg")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.set_content(f"<html><body style='margin:0;background:#0B132B'>{svg}</body></html>")
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(HERE / "cover.png"))
            b.close()
        print("wrote", HERE / "cover.png")
    except Exception as e:  # noqa: BLE001 - PNG is a convenience
        print("png skipped:", type(e).__name__)
