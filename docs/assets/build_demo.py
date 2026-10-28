#!/usr/bin/env python3
"""Builds docs/assets/demo.gif from real command output captured in docs/assets/demo/ (rich `--ui` output with ANSI colours).

    python docs/assets/build_demo.py

To refresh the captures run each command with FINSOCNET_UI_COLOR=1 COLUMNS=118 and save stdout next to its .ansi / .txt name.
"""

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DEMO = HERE / "demo"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SIZE, COLS, ROWS = 15, 118, 22
CW, LH = 9, 21
PADX, PADY, BAR = 22, 14, 34
W, H = COLS * CW + 2 * PADX, ROWS * LH + 2 * PADY + BAR
BG, FG, DIM, PROMPT = (11, 19, 43), (226, 232, 248), (120, 134, 170), (0, 255, 163)
ANSI = {30: (60, 70, 90), 31: (255, 107, 107), 32: (0, 255, 163), 33: (255, 214, 102), 34: (110, 160, 255), 35: (200, 130, 255), 36: (0, 240, 255), 37: FG}
font, bold = ImageFont.truetype(FONT, SIZE), ImageFont.truetype(BOLD, SIZE)

SCENES = [
    ("finsocnet explore add \"pairs trading\"", "explore.txt", 1.3),
    ("stackexchange.py search \"pairs trading cointegration\" --site quant --new-only --ui", "visited.ansi", 2.2),
    ("finsocnet search \"how to size a position after a losing streak\" --types cards --ui", "search.ansi", 3.4),
    ("rea.py fetch /bin/ls --kind detect --ui", "rea.ansi", 2.2),
    ("site.py probe https://lobste.rs   # robots.txt says: no crawlers", "probe.txt", 2.8),
]


def parse(line: str) -> list[tuple[str, tuple[int, int, int], bool]]:
    out, color, bold_on, dim = [], FG, False, False
    pos = 0
    for m in re.finditer(r"\x1b\[([0-9;]*)m", line):
        if m.start() > pos:
            out.append((line[pos:m.start()], DIM if dim else color, bold_on))
        codes = [int(c) for c in m.group(1).split(";") if c] or [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                color, bold_on, dim = FG, False, False
            elif c == 1:
                bold_on = True
            elif c == 2:
                dim = True
            elif 30 <= c <= 37:
                color = ANSI[c]
            elif 90 <= c <= 97:
                color = ANSI[c - 60]
            elif c == 39:
                color = FG
            elif c == 38 and i + 1 < len(codes) and codes[i + 1] == 2 and i + 4 < len(codes):
                color = tuple(codes[i + 2:i + 5])
                i += 4
            elif c == 38 and i + 1 < len(codes) and codes[i + 1] == 5 and i + 2 < len(codes):
                n = codes[i + 2]
                color = ANSI.get(30 + n % 8, FG) if n < 16 else (180, 190, 215)
                i += 2
            i += 1
        pos = m.end()
    if pos < len(line):
        out.append((line[pos:], DIM if dim else color, bold_on))
    return out


def frame(lines: list[str], typed: str | None, cursor: bool) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W - 1, H - 1), 12, outline=(40, 56, 100), fill=BG)
    d.rectangle((1, 1, W - 2, BAR), fill=(22, 35, 77))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse((16 + i * 22, 11, 28 + i * 22, 23), fill=c)
    d.text((W // 2, 12), "finsocnet", fill=DIM, font=font, anchor="mt")
    y = BAR + PADY
    shown = lines[-(ROWS - 1):] if typed is not None else lines[-ROWS:]
    for ln in shown:
        x = PADX
        for text, color, b in parse(ln):
            d.text((x, y), text, fill=color, font=bold if b else font)
            x += len(text) * CW
        y += LH
    if typed is not None:
        d.text((PADX, y), "$", fill=PROMPT, font=bold)
        d.text((PADX + 2 * CW, y), typed + ("▌" if cursor else ""), fill=FG, font=font)
    return im


def build() -> None:
    frames: list[Image.Image] = []
    durs: list[int] = []

    def add(im: Image.Image, ms: int) -> None:
        frames.append(im)
        durs.append(ms)

    for cmd, fname, hold in SCENES:
        text = (DEMO / fname).read_text(encoding="utf-8", errors="replace")
        raw = [l.rstrip() for l in text.splitlines()]
        raw = [l for l in raw if l.strip() != ""] if fname.endswith(".txt") else raw[:ROWS - 2]
        if fname == "rea.ansi":
            raw = raw[:14]
        add(frame([], "", True), 350)
        for i in range(0, len(cmd) + 1, 3):
            add(frame([], cmd[:i], True), 45)
        add(frame([], cmd, False), 260)
        shown: list[str] = []
        for ln in raw:
            shown.append(ln)
            add(frame(shown, None, False), 70)
        add(frame(shown, None, False), int(hold * 1000))
    # a closing frame with the pitch
    end = frame([], None, False)
    d = ImageDraw.Draw(end)
    d.text((W // 2, H // 2 - 30), "FinSocNet", fill=(255, 255, 255), font=ImageFont.truetype(BOLD, 40), anchor="mm")
    d.text((W // 2, H // 2 + 14), "explore · remember · search by meaning", fill=PROMPT, font=ImageFont.truetype(FONT, 20), anchor="mm")
    add(end, 2600)
    pal = [f.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(HERE / "demo.gif", save_all=True, append_images=pal[1:], duration=durs, loop=0, optimize=True, disposal=1)
    print("wrote", HERE / "demo.gif", len(frames), "frames,", round((HERE / 'demo.gif').stat().st_size / 1024), "KB")


if __name__ == "__main__":
    build()
