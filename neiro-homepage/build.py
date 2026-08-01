#!/usr/bin/env python3
import base64
import io
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(HERE, "photos")
STICKER_SRC = os.path.join(HERE, "..", "neiro-sticker", "neiro_sticker_v1.png")
TEMPLATE = os.path.join(HERE, "template.html")
OUT = os.path.join(HERE, "site.html")

GALLERY_FILES = [
    "IMG20211031105715.jpg",
    "IMG20240303151314.jpg",
    "IMG20240303151323.jpg",
    "IMG_5985.jpg",
    "IMG_5986.jpg",
    "IMG_5988.jpg",
    "IMG_7099.jpg",
    "IMG_7100.jpg",
    "IMG_7101.jpg",
    "IMG_7102.jpg",
]
AVATAR_FILE = "channels4_profile.jpg"


def to_data_uri(path, max_w, fmt="JPEG", quality=68):
    im = Image.open(path)
    if fmt == "JPEG":
        im = im.convert("RGB")
    else:
        im = im.convert("RGBA")
    if im.width > max_w:
        h = round(im.height * max_w / im.width)
        im = im.resize((max_w, h), Image.LANCZOS)
    buf = io.BytesIO()
    if fmt == "JPEG":
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        im.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}", len(buf.getvalue())


def main():
    total = 0
    gallery_html = []
    for i, fname in enumerate(GALLERY_FILES):
        path = os.path.join(PHOTOS_DIR, fname)
        uri, size = to_data_uri(path, max_w=760, quality=66)
        total += size
        gallery_html.append(
            f'<figure class="polaroid"><img src="{uri}" alt="ねいろの写真" /></figure>'
        )

    avatar_uri, size = to_data_uri(os.path.join(PHOTOS_DIR, AVATAR_FILE), max_w=200, quality=72)
    total += size

    sticker_uri, size = to_data_uri(STICKER_SRC, max_w=520, fmt="PNG")
    total += size

    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("@@GALLERY@@", "\n      ".join(gallery_html))
    html = html.replace("@@AVATAR@@", avatar_uri)
    html = html.replace("@@STICKER@@", sticker_uri)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"embedded image bytes total: {total/1024:.0f} KB")
    print(f"output html size: {os.path.getsize(OUT)/1024:.0f} KB")


if __name__ == "__main__":
    main()
