"""Generate multi-size snowflake .ico for Snow v3 desktop shortcut."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = Path(__file__).parent
ICO_PATH = OUT_DIR / "snow.ico"
PNG_PATH = OUT_DIR / "snow_icon_256.png"


def draw_snowflake(size: int) -> Image.Image:
    """Crisp geometric snowflake icon with soft glow, transparent bg."""
    s = size * 4  # draw 4x then downscale for AA
    cx = cy = s / 2.0
    r = s * 0.42

    plate = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    pad = int(s * 0.06)

    # soft outer aura rings
    for i in range(8):
        t = i / 7
        a = int(40 + 50 * (1 - t))
        rr = int(s * 0.48 * (1 - t * 0.08))
        col = (120 + int(40 * t), 160 + int(30 * t), 190 + int(20 * t), a)
        pd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)

    # glass disk
    pd.ellipse([pad, pad, s - pad, s - pad], fill=(28, 42, 58, 220))

    # top highlight
    hl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    hld = ImageDraw.Draw(hl)
    hld.ellipse(
        [s * 0.18, s * 0.12, s * 0.82, s * 0.55],
        fill=(180, 220, 255, 55),
    )
    plate = Image.alpha_composite(plate, hl)

    flake = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    fd = ImageDraw.Draw(flake)

    def line(p1, p2, w, color):
        fd.line([p1, p2], fill=color, width=max(1, int(w)))

    def arm(angle_deg):
        a = math.radians(angle_deg)
        x2 = cx + r * math.cos(a)
        y2 = cy + r * math.sin(a)
        main_w = s * 0.055
        glow_w = s * 0.09

        line((cx, cy), (x2, y2), glow_w, (160, 210, 255, 70))
        line((cx, cy), (x2, y2), main_w, (235, 248, 255, 255))

        # tip diamond
        tip_r = s * 0.06
        diamond = []
        for da in (0, 90, 180, 270):
            rad = math.radians(angle_deg + da)
            diamond.append(
                (x2 + tip_r * 0.7 * math.cos(rad), y2 + tip_r * 0.7 * math.sin(rad))
            )
        fd.polygon(diamond, fill=(255, 255, 255, 255))

        # side branches
        for frac, br_len, br_ang in ((0.42, 0.22, 38), (0.68, 0.16, 42)):
            bx = cx + r * frac * math.cos(a)
            by = cy + r * frac * math.sin(a)
            for sign in (-1, 1):
                ba = math.radians(angle_deg + sign * br_ang)
                ex = bx + r * br_len * math.cos(ba)
                ey = by + r * br_len * math.sin(ba)
                line((bx, by), (ex, ey), main_w * 0.72, (220, 240, 255, 245))
                tr = s * 0.025
                fd.ellipse([ex - tr, ey - tr, ex + tr, ey + tr], fill=(255, 255, 255, 255))

        # nodes along arm
        for frac in (0.28, 0.55):
            nx = cx + r * frac * math.cos(a)
            ny = cy + r * frac * math.sin(a)
            nr = s * 0.028
            fd.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=(200, 230, 255, 255))

    # 6-fold classic snowflake (vertical arm up)
    for i in range(6):
        arm(i * 60 - 90)

    # center hex
    hex_r = s * 0.09
    hex_pts = [
        (cx + hex_r * math.cos(math.radians(i * 60 - 90)),
         cy + hex_r * math.sin(math.radians(i * 60 - 90)))
        for i in range(6)
    ]
    fd.polygon(hex_pts, fill=(255, 255, 255, 255))
    hex_r2 = s * 0.045
    hex_pts2 = [
        (cx + hex_r2 * math.cos(math.radians(i * 60 - 90)),
         cy + hex_r2 * math.sin(math.radians(i * 60 - 90)))
        for i in range(6)
    ]
    fd.polygon(hex_pts2, fill=(140, 190, 230, 255))

    out = Image.alpha_composite(plate, flake)
    glow = out.filter(ImageFilter.GaussianBlur(radius=max(1, s // 80)))
    base = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    base = Image.alpha_composite(base, glow)
    base = Image.alpha_composite(base, out)
    return base.resize((size, size), Image.Resampling.LANCZOS)


def save_multi_ico(path: Path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    """Write a true multi-resolution ICO with independently rendered sizes."""
    images = [draw_snowflake(sz) for sz in sizes]
    images[-1].save(PNG_PATH)
    # Pillow: pass the largest and list of sizes — it resamples.
    # For sharp multi-size, use IcoImagePlugin via save with append of custom frames:
    # Best approach: save 256 as base with sizes=; also write using ico writer manually.
    images[0].save(
        path,
        format="ICO",
        sizes=[(sz, sz) for sz in sizes],
        append_images=images[1:],
    )
    # Some Pillow versions ignore append_images for ICO — fallback write from 256
    if path.stat().st_size < 1000:
        images[-1].save(path, format="ICO", sizes=[(sz, sz) for sz in sizes])


if __name__ == "__main__":
    save_multi_ico(ICO_PATH)
    print(f"Wrote {ICO_PATH} ({ICO_PATH.stat().st_size} bytes)")
    print(f"Wrote {PNG_PATH} ({PNG_PATH.stat().st_size} bytes)")
    im = Image.open(ICO_PATH)
    print(f"ICO open OK: mode={im.mode} size={im.size}")
