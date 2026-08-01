#!/usr/bin/env python3
"""コマごとの大きさ・位置のズレを揃える

AI生成のコマは1枚ずつ微妙に大きさ・位置が違うので、そのまま並べると
アニメがガタガタする。そこで:
  1. 透明部分を除いた「犬の実体」の範囲(bbox)を取る
  2. 高さが同じになるように拡大縮小
  3. 足元(下辺)を基準に、左右中央でキャンバスに置き直す
"""
from PIL import Image
import glob, os

SRC = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "frames", "f*.png")))
OUTDIR = os.path.join(os.path.dirname(__file__), "frames_norm")
os.makedirs(OUTDIR, exist_ok=True)

TARGET_H = 240          # 犬の高さをこの値に揃える
CANVAS = (420, 300)     # 出力キャンバス（余白込み）
BASELINE = 285          # 足元をキャンバスのこの高さに置く

for i, path in enumerate(SRC):
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()          # 透明でない範囲
    if bbox is None:
        print(f"  {os.path.basename(path)}: 中身が空 -> スキップ")
        continue
    dog = im.crop(bbox)
    w, h = dog.size
    scale = TARGET_H / h
    dog = dog.resize((max(1, round(w * scale)), TARGET_H), Image.LANCZOS)

    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    x = (CANVAS[0] - dog.size[0]) // 2
    y = BASELINE - dog.size[1]
    canvas.paste(dog, (x, y), dog)
    canvas.save(os.path.join(OUTDIR, f"n{i:02d}.png"))
    print(f"  {os.path.basename(path)}: bbox={bbox} 元サイズ={w}x{h} -> 幅{dog.size[0]}")

# --- 確認用: 12コマを並べた一覧をチェック柄の上に作る ---
files = sorted(glob.glob(os.path.join(OUTDIR, "n*.png")))
cols, rows = 4, 3
sheet = Image.new("RGB", (CANVAS[0] * cols, CANVAS[1] * rows), (255, 255, 255))
# チェック柄（透明部分が分かるように）
for by in range(0, sheet.size[1], 20):
    for bx in range(0, sheet.size[0], 20):
        if (bx // 20 + by // 20) % 2 == 0:
            sheet.paste((220, 220, 220), (bx, by, min(bx + 20, sheet.size[0]), min(by + 20, sheet.size[1])))
for i, f in enumerate(files):
    im = Image.open(f).convert("RGBA")
    sheet.paste(im, ((i % cols) * CANVAS[0], (i // cols) * CANVAS[1]), im)
sheet.save(os.path.join(os.path.dirname(__file__), "check_frames.png"))
print(f">>> {len(files)}コマ整列完了 -> frames_norm/ , 確認用 check_frames.png")
