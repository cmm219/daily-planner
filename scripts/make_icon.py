"""Generate planner_icon.ico — a clean checkbox icon (black square + blue check),
replacing Flet's default pink/blue logo. Re-run to regenerate.

    python scripts/make_icon.py
"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "planner_icon.ico")

S = 256
BG = (13, 17, 23, 255)       # #0d1117
BLUE = (88, 166, 255, 255)    # #58a6ff
BORDER = (48, 54, 61, 255)    # #30363d


def render(size):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Black rounded app tile with a subtle border.
    d.rounded_rectangle([6, 6, S - 6, S - 6], radius=52, fill=BG, outline=BORDER, width=6)
    # Checkbox: rounded square outline in blue.
    d.rounded_rectangle([62, 62, 194, 194], radius=22, outline=BLUE, width=12)
    # Blue checkmark (slightly overhangs the box, top-right, for a confident tick).
    d.line([(92, 132), (122, 164)], fill=BLUE, width=22, joint="curve")
    d.line([(122, 164), (182, 86)], fill=BLUE, width=22, joint="curve")
    return img.resize((size, size), Image.LANCZOS)


def main():
    base = render(S)
    sizes = [16, 32, 48, 64, 128, 256]
    base.save(OUT, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
