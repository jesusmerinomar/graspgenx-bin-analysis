#!/usr/bin/env python3
"""Header banner: the before/after of the regeneration, over a frame of the cell running
in Isaac Sim with the same box in shot.

    python scripts/make_hero.py

Background: figures/src/frame_cell.jpg, a frame of the cell's own recording (the flat
cable and the drill are the objects inside the box). Panels: rendered from
data/seed7/{regen_off,regen_on}.npz by scripts/make_visor_shot.py.
"""
import importlib.util, json, os, sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "figures", "src", "frame_cell.jpg")
D = os.path.join(HERE, "..", "data", "seed7")
OUT = os.path.join(HERE, "..", "figures", "hero.png")
W, H = 2400, 1210
BG, INK, DIM, GREEN, RED = (12, 14, 18), (244, 246, 249), (152, 160, 172), (45, 200, 105), (222, 70, 60)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = lambda s, b=False: ImageFont.truetype(FB if b else F, s)

def panels():
    spec = importlib.util.spec_from_file_location("vs", os.path.join(HERE, "make_visor_shot.py"))
    vs = importlib.util.module_from_spec(spec); sys.argv = ["x"]
    try: spec.loader.exec_module(vs)
    except SystemExit: pass
    b = json.load(open(os.path.join(D, "box_geometry.json")))
    out = []
    for tag in ("regen_off", "regen_on"):
        png = os.path.join(HERE, "..", "figures", "src", f"panel_{tag}.png")
        n, ok = vs.render_panel(os.path.join(D, f"{tag}.npz"), b, png, size=(6.6, 5.4), dpi=170)
        out.append((Image.open(png).convert("RGB"), n, ok))
    return out

def main() -> int:
    src = Image.open(SRC).convert("RGB")
    scene = src.crop((720, 470, 1844, 1360))
    canvas = Image.new("RGB", (W, H), BG)
    r = max(W / scene.width, H / scene.height)
    bg = scene.resize((int(scene.width * r), int(scene.height * r)), Image.LANCZOS)
    canvas.paste(bg, ((W - bg.width) // 2, (H - bg.height) // 2))
    canvas = ImageEnhance.Brightness(canvas).enhance(0.30)          # the render stays as texture, not subject
    canvas = ImageEnhance.Color(canvas).enhance(0.75)
    d = ImageDraw.Draw(canvas)

    d.text((W // 2, 52), "G R A S P G E N - X   I N S I D E   A   C O N T A I N E R",
           font=font(23, True), fill=DIM, anchor="ma")
    d.text((W // 2, 100), "400 grasps proposed. Three of them fit.", font=font(58, True), fill=INK, anchor="ma")
    d.text((W // 2, 178), "What a cardboard box does to an off-the-shelf grasp generator, and what "
                          "regenerating the candidates recovers.", font=font(26), fill=DIM, anchor="ma")

    ps = panels()
    pw = 820
    cards = [(p.resize((pw, int(p.height * pw / p.width)), Image.LANCZOS), n, ok) for p, n, ok in ps]
    gap, top = 100, 300
    x0 = (W - (2 * pw + gap)) // 2
    for i, (card, n, ok) in enumerate(cards):
        x = x0 + i * (pw + gap)
        sh = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle([40, 40, card.width + 40, card.height + 40], fill=(0, 0, 0, 200))
        bx = (x - 40, top - 40, x + card.width + 40, top + card.height + 40)
        canvas.paste(Image.alpha_composite(canvas.crop(bx).convert("RGBA"),
                                           sh.filter(ImageFilter.GaussianBlur(24))).convert("RGB"), bx[:2])
        canvas.paste(card, (x, top))
        d.rectangle([x - 1, top - 1, x + card.width, top + card.height], outline=(88, 94, 106), width=2)
        cx = x + card.width // 2
        d.text((cx, top - 56), ("as sampled", "after constraint-aware regeneration")[i],
               font=font(30, True), fill=INK, anchor="ma")
        d.text((cx, top + card.height + 26), f"{ok}", font=font(72, True),
               fill=GREEN if i else DIM, anchor="ma")
        d.text((cx, top + card.height + 122), f"usable of the {n} candidates",
               font=font(25), fill=DIM, anchor="ma")

    y = H - 52
    d.text((W // 2 - 300, y), "──", font=font(24, True), fill=GREEN, anchor="ma")
    d.text((W // 2 - 276, y - 4), "clears the walls, the floor, the neighbours and the descent", font=font(23), fill=DIM)
    d.text((W // 2 + 470, y), "──", font=font(24, True), fill=RED, anchor="ma")
    d.text((W // 2 + 494, y - 4), "killed by the box", font=font(23), fill=DIM)

    canvas.save(OUT, quality=95)
    print("written", OUT, canvas.size)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
