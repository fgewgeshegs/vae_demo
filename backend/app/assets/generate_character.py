"""Generate Q版小老师 (cute chibi teacher) character PNG with transparent background."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw


def create_teacher_character(
    size: tuple[int, int] = (240, 320),
) -> Image.Image:
    """Draw a cute chibi-style teacher character on transparent background.

    Returns a RGBA Image ready to be saved as PNG or used in overlay.
    """
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = w // 2, h // 2
    head_top = 20

    # --- colors ---
    skin = (255, 224, 204, 255)
    hair = (60, 40, 30, 255)
    eye = (40, 30, 20, 255)
    cheek = (255, 180, 160, 160)
    shirt = (230, 240, 250, 255)
    collar = (200, 50, 50, 255)
    book_c = (80, 60, 160, 255)
    book_p = (220, 200, 100, 255)
    pant = (60, 60, 80, 255)

    # --- head (round) ---
    head_r = 55
    head_y = head_top + head_r
    draw.ellipse(
        [cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
        fill=skin,
    )

    # --- hair (bob cut with small pigtails) ---
    for side, dx in [(-1, -3), (1, 3)]:
        # Main hair dome
        draw.ellipse(
            [cx + dx - head_r - 5, head_y - head_r - 8,
             cx + dx + head_r + 5, head_y + head_r - 15],
            fill=hair,
        )
        # Pigtail tuft
        for dy_off in [10, 25, 40]:
            px = cx + side * (head_r + 6)
            py = head_y - head_r // 2 + dy_off
            draw.ellipse([px - 9, py - 6, px + 9, py + 6], fill=hair)
        # Hair clip
        clip_x = cx + side * (head_r - 8)
        clip_y = head_y - head_r // 2 + 5
        clip_c = (240, 100, 140, 255)
        draw.ellipse([clip_x - 4, clip_y - 4, clip_x + 4, clip_y + 4], fill=clip_c)

    # Bangs (front hair)
    for i in range(7):
        bx = cx + (i - 3) * 12
        by = head_y - head_r + 5
        draw.ellipse([bx - 8, by - 10, bx + 8, by + 5], fill=hair)

    # --- eyes (big, cute) ---
    eye_spacing = 18
    eye_y = head_y + 5
    for side in [-1, 1]:
        ex = cx + side * eye_spacing
        draw.ellipse([ex - 10, eye_y - 8, ex + 10, eye_y + 8], fill=(255, 255, 255, 255))
        draw.ellipse([ex - 5, eye_y - 5, ex + 5, eye_y + 5], fill=eye)
        draw.ellipse([ex - 2, eye_y - 6, ex + 2, eye_y - 2], fill=(255, 255, 255, 220))

    # --- blush ---
    for side in [-1, 1]:
        bx = cx + side * 28
        by = eye_y + 10
        draw.ellipse([bx - 8, by - 4, bx + 8, by + 4], fill=cheek)

    # --- mouth ---
    mouth_y = eye_y + 16
    draw.arc([cx - 6, mouth_y - 3, cx + 6, mouth_y + 5], 200, 340,
             fill=(180, 100, 100, 220), width=2)

    # --- body ---
    body_top = head_y + head_r - 5
    body_w = 80
    body_h = 60
    draw.rounded_rectangle(
        [cx - body_w // 2, body_top, cx + body_w // 2, body_top + body_h],
        radius=15, fill=shirt,
    )
    tie_pts = [
        (cx - 6, body_top + 2), (cx + 6, body_top + 2),
        (cx + 3, body_top + 20), (cx, body_top + 28),
        (cx - 3, body_top + 20),
    ]
    draw.polygon(tie_pts, fill=collar)
    draw.polygon([(cx - 14, body_top + 2), (cx - 4, body_top + 2), (cx - 8, body_top + 14)],
                 fill=(255, 255, 255, 200))
    draw.polygon([(cx + 4, body_top + 2), (cx + 14, body_top + 2), (cx + 8, body_top + 14)],
                 fill=(255, 255, 255, 200))

    # --- arms ---
    arm_top = body_top + 10
    for side, off in [(-1, -20), (1, 20)]:
        ax = cx + side * (body_w // 2 + 5)
        draw.ellipse([ax - 5, arm_top, ax + 5, arm_top + 30], fill=skin)

    # --- book in left hand ---
    book_x = cx - 35
    book_y = body_top + 18
    draw.rounded_rectangle([book_x, book_y, book_x + 30, book_y + 22], radius=3, fill=book_c)
    draw.rounded_rectangle([book_x + 3, book_y + 2, book_x + 27, book_y + 20], radius=2, fill=book_p)
    draw.line([(book_x + 1, book_y), (book_x + 1, book_y + 22)], fill=(50, 30, 120, 200), width=2)

    # --- pointer in right hand ---
    ptr_x = cx + 30
    ptr_y = body_top + 5
    draw.line([(ptr_x, ptr_y), (ptr_x - 15, body_top + 40)], fill=(180, 120, 60, 255), width=3)
    draw.polygon([
        (ptr_x - 16, body_top + 40), (ptr_x - 18, body_top + 46),
        (ptr_x - 22, body_top + 40),
    ], fill=(255, 50, 50, 255))

    # --- legs ---
    leg_top = body_top + body_h - 5
    for side in [-1, 1]:
        lx = cx + side * 15
        draw.rectangle([lx - 8, leg_top, lx + 8, leg_top + 30], fill=pant)
        draw.ellipse([lx - 10, leg_top + 26, lx + 10, leg_top + 36], fill=(40, 40, 50, 255))

    return img


def save_character_asset(dest: str | Path) -> Path:
    """Generate and save the teacher character PNG to dest."""
    dest = Path(dest)
    img = create_teacher_character()
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest), "PNG")
    return dest


if __name__ == "__main__":
    out = Path(__file__).parent / "teacher_character.png"
    save_character_asset(out)
    print(f"Character saved to {out}")
