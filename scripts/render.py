"""Render a post's slides to 1080x1350 PNG carousel images (no AI images of real people)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import ROOT, settings

W, H = 1080, 1350
PAD = 90
FONTS = ROOT / "assets" / "fonts"


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines: list[str] = []
    for para in str(text).split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=f) <= width:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


def fit(draw, text, weight, start, minimum, width, max_h, spacing=1.25):
    size = start
    while size >= minimum:
        f = font(weight, size)
        lines = wrap(draw, text, f, width)
        if len(lines) * size * spacing <= max_h:
            return f, lines, size
        size -= 4
    f = font(weight, minimum)
    return f, wrap(draw, text, f, width), minimum


def frame(b: dict, label: str, idx: int, total: int, as_of: str, handle: str):
    img = Image.new("RGB", (W, H), b["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=b["accent"])
    d.text((PAD, 60), f"@{handle}", font=font("Medium", 30), fill=b["muted"])
    counter = f"{idx}/{total}"
    d.text((W - PAD - d.textlength(counter, font=font("Medium", 30)), 60), counter,
           font=font("Medium", 30), fill=b["muted"])
    # status pill
    pf = font("Bold", 30)
    tw = d.textlength(label, font=pf)
    color = b["labels"].get(label, b["muted"])
    d.rounded_rectangle([PAD, 130, PAD + tw + 48, 186], radius=28, fill=color)
    d.text((PAD + 24, 136), label, font=pf, fill="#FFFFFF")
    # footer
    d.line([PAD, H - 140, W - PAD, H - 140], fill=b["panel"], width=3)
    d.text((PAD, H - 115), f"Status as of {as_of}  ·  Sources in caption",
           font=font("Regular", 28), fill=b["muted"])
    return img, d


def render_post(post: dict, out_dir: Path) -> list[Path]:
    cfg = settings()
    b, handle = cfg["brand"], cfg["page"]["handle"]
    label, as_of = post["status_label"], post["as_of"]
    slides = post["slides"]
    total = len(slides) + 1
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    width = W - 2 * PAD

    # cover
    img, d = frame(b, label, 1, total, as_of, handle)
    kicker = "UPDATE" if post.get("kind") == "update" else post.get("category", "").upper()
    if kicker:
        d.text((PAD, 300), kicker, font=font("Bold", 36), fill=b["accent"])
    f, lines, size = fit(d, post["headline"], "Bold", 104, 60, width, 620)
    y = 370
    for ln in lines:
        d.text((PAD, y), ln, font=f, fill=b["text"])
        y += int(size * 1.15)
    sf = font("Medium", 40)
    d.text((PAD, H - 240), "Swipe", font=sf, fill=b["accent"])
    ax, ay = PAD + d.textlength("Swipe", font=sf) + 24, H - 212
    d.line([ax, ay, ax + 50, ay], fill=b["accent"], width=5)
    d.polygon([(ax + 50, ay - 12), (ax + 66, ay), (ax + 50, ay + 12)], fill=b["accent"])
    p = out_dir / "slide_01.png"
    img.save(p)
    paths.append(p)

    for i, s in enumerate(slides, start=2):
        img, d = frame(b, label, i, total, as_of, handle)
        tf, tlines, tsize = fit(d, s["title"], "Bold", 68, 44, width, 260)
        y = 260
        for ln in tlines:
            d.text((PAD, y), ln, font=tf, fill=b["accent"])
            y += int(tsize * 1.2)
        y += 40
        bf, blines, bsize = fit(d, s["body"], "Regular", 50, 32, width, H - 200 - y, 1.45)
        for ln in blines:
            d.text((PAD, y), ln, font=bf, fill=b["text"])
            y += int(bsize * 1.45)
        p = out_dir / f"slide_{i:02d}.png"
        img.save(p)
        paths.append(p)
    return paths


if __name__ == "__main__":
    import json, sys
    post_dir = Path(sys.argv[1])
    render_post(json.loads((post_dir / "post.json").read_text(encoding="utf-8")), post_dir)
