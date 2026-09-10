#!/usr/bin/env python3
"""Header banner: the box as the cell sees it, and underneath what the grasp generator
proposes for the cable in it, before and after regenerating the candidates.

    python scripts/make_hero.py

Photo: figures/src/frame_cell.jpg, a frame of the cell's own recording.
Panels: rendered from data/seed7/{regen_off,regen_on}.npz by scripts/make_visor_shot.py.
"""
import importlib.util, json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "figures", "src", "frame_cell.jpg")
D = os.path.join(HERE, "..", "data", "seed7")
OUT = os.path.join(HERE, "..", "figures", "hero.png")
W = 2400
BG, INK, DIM, GREEN, RED = (13, 15, 19), (244, 246, 249), (150, 158, 170), (45, 200, 105), (222, 70, 60)
FT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = lambda s, b=False: ImageFont.truetype(FB if b else FT, s)
RADIUS = 26

def rounded(img, radius=RADIUS):
    """Copy of img with rounded corners, as RGBA."""
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius, fill=255)
    out = img.convert("RGBA"); out.putalpha(m)
    return out

def place(canvas, img, xy, radius=RADIUS):
    """Paste with rounded corners and a soft drop shadow."""
    card = rounded(img, radius)
    pad = 46
    sh = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 8, pad + card.width, pad + card.height + 8],
                                         radius, fill=(0, 0, 0, 205))
    sh = sh.filter(ImageFilter.GaussianBlur(26))
    canvas.alpha_composite(sh, (xy[0] - pad, xy[1] - pad))
    canvas.alpha_composite(card, xy)

def panels():
    spec = importlib.util.spec_from_file_location("vs", os.path.join(HERE, "make_visor_shot.py"))
    vs = importlib.util.module_from_spec(spec); sys.argv = ["x"]
    try: spec.loader.exec_module(vs)
    except SystemExit: pass
    b = json.load(open(os.path.join(D, "box_geometry.json")))
    out = []
    for tag in ("regen_off", "regen_on"):
        png = os.path.join(HERE, "..", "figures", "src", f"panel_{tag}.png")
        n, ok = vs.render_panel(os.path.join(D, f"{tag}.npz"), b, png, size=(6.6, 5.2), dpi=170)
        out.append((Image.open(png).convert("RGB"), n, ok))
    return out

def main() -> int:
    photo = Image.open(SRC).convert("RGB").crop((980, 540, 1844, 1240))
    pw_photo = 980
    photo = photo.resize((pw_photo, int(photo.height * pw_photo / photo.width)), Image.LANCZOS)

    ps = panels()
    pw = 820
    cards = [(p.resize((pw, int(p.height * pw / p.width)), Image.LANCZOS), n, ok) for p, n, ok in ps]
    gap = 168
    y_photo, y_panels = 250, 250 + photo.height + 190
    H = y_panels + cards[0][0].height + 250

    canvas = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(canvas)
    d.text((W // 2, 60), "G R A S P G E N - X   I N S I D E   A   C O N T A I N E R",
           font=font(23, True), fill=DIM, anchor="ma")
    d.text((W // 2, 108), "400 grasps proposed. Three of them fit.", font=font(58, True), fill=INK, anchor="ma")
    d.text((W // 2, 186), "What a cardboard box does to an off-the-shelf grasp generator, and what "
                          "regenerating the candidates recovers.", font=font(26), fill=DIM, anchor="ma")

    place(canvas, photo, ((W - photo.width) // 2, y_photo))
    d.text((W // 2, y_photo + photo.height + 34),
           "the cell: a flat USB-C cable and a drill inside a 38 × 18 × 14 cm box",
           font=font(25), fill=DIM, anchor="ma")

    x0 = (W - (2 * pw + gap)) // 2
    for i, (card, n, ok) in enumerate(cards):
        x = x0 + i * (pw + gap)
        d.text((x + pw // 2, y_panels - 56), ("as sampled", "after constraint-aware regeneration")[i],
               font=font(30, True), fill=INK, anchor="ma")
        place(canvas, card, (x, y_panels))
        cx, by = x + pw // 2, y_panels + card.height
        d.text((cx, by + 30), f"{ok}", font=font(72, True), fill=GREEN if i else DIM, anchor="ma")
        d.text((cx, by + 126), f"usable of the {n} candidates for the cable",
               font=font(24), fill=DIM, anchor="ma")

    # the arrow between the two panels, with the factor it stands for
    ax_ = x0 + pw + gap // 2
    ay = y_panels + cards[0][0].height // 2
    d.ellipse([ax_ - 62, ay - 62, ax_ + 62, ay + 62], fill=(22, 26, 32), outline=GREEN, width=3)
    d.line([(ax_ - 34, ay), (ax_ + 12, ay)], fill=GREEN, width=9)
    d.polygon([(ax_ + 4, ay - 24), (ax_ + 36, ay), (ax_ + 4, ay + 24)], fill=GREEN)
    n0, n1 = cards[0][2], cards[1][2]
    d.text((ax_, ay + 86), f"× {n1 / n0:.0f}", font=font(38, True), fill=GREEN, anchor="ma")

    y = H - 52
    d.text((W // 2 - 300, y), "──", font=font(24, True), fill=GREEN, anchor="ma")
    d.text((W // 2 - 276, y - 4), "clears the walls, the floor, the neighbours and the descent",
           font=font(23), fill=DIM)
    d.text((W // 2 + 470, y), "──", font=font(24, True), fill=RED, anchor="ma")
    d.text((W // 2 + 494, y - 4), "killed by the box", font=font(23), fill=DIM)

    canvas.convert("RGB").save(OUT, quality=95)
    print("written", OUT, (W, H))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
