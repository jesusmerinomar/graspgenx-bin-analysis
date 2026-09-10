#!/usr/bin/env python3
"""Header banner: a frame of the cell running in Isaac Sim, with the sampler's candidates
for the object in the box blown up on the right.

    python scripts/make_hero.py

Source frame: figures/src/frame_cell.jpg (2304x1440, from the cell's own recording; the
small panel in its top-right corner is the live candidate view, red rejected / green kept).
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "figures", "src", "frame_cell.jpg")
OUT = os.path.join(HERE, "..", "figures", "hero.png")
W, H = 2400, 900
BG, INK, DIM, ACCENT = (14, 16, 20), (242, 244, 247), (150, 158, 170), (55, 214, 122)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def font(sz, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, sz)

def main() -> int:
    src = Image.open(SRC).convert("RGB")
    scene = src.crop((700, 350, 1844, 1320))              # the box with the objects, and the arm above
    inset = src.crop((1856, 20, 2290, 560))               # the live candidate view

    canvas = Image.new("RGB", (W, H), BG)
    r = H / scene.height
    bg = scene.resize((int(scene.width * r), H), Image.LANCZOS)
    canvas.paste(bg, (W - bg.width, 0))
    shade = Image.new("L", (W, H), 0)                      # fade the render into the dark panel
    ds = ImageDraw.Draw(shade)
    x0 = W - bg.width
    for x in range(W):
        v = 255 if x < x0 else max(0, int(255 * (1 - (x - x0) / 340)))
        ds.line([(x, 0), (x, H)], fill=v)
    canvas.paste(Image.new("RGB", (W, H), BG), (0, 0), shade)

    # the candidate view, as a card straddling the seam
    card = inset.resize((470, int(inset.height * 470 / inset.width)), Image.LANCZOS)
    cx, cy = x0 - 330, (H - card.height) // 2
    sh = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([40, 40, card.width + 40, card.height + 40], fill=(0, 0, 0, 190))
    box = (cx - 40, cy - 40, cx + card.width + 40, cy + card.height + 40)
    canvas.paste(Image.alpha_composite(canvas.crop(box).convert("RGBA"),
                                       sh.filter(ImageFilter.GaussianBlur(22))).convert("RGB"), box[:2])
    canvas.paste(card, (cx, cy))
    d = ImageDraw.Draw(canvas)
    d.rectangle([cx - 1, cy - 1, cx + card.width, cy + card.height], outline=(96, 102, 114), width=2)
    d.text((cx, cy + card.height + 22), "400 candidates for one object in the box",
           font=font(21), fill=DIM)
    d.text((cx, cy + card.height + 52), "red rejected · green kept", font=font(21), fill=DIM)

    d.text((100, 292), "GRASPGEN-X", font=font(30, True), fill=ACCENT)
    d.text((100, 342), "inside a container", font=font(62, True), fill=INK)
    for i, line in enumerate(["Bin-picking measurements on top of NVIDIA's",
                              "grasp generator: what a cardboard box does to",
                              "its candidates, and what we do about it."]):
        d.text((102, 444 + 40 * i), line, font=font(28), fill=DIM)
    d.text((102, 604), "UR5e · WSG-50 · Isaac Sim · rigid objects and FEM garments",
           font=font(23), fill=(110, 118, 130))

    canvas.save(OUT, quality=95)
    print("written", OUT, canvas.size)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
