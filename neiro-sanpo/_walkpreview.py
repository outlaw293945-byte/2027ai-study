"""歩き方だけを確かめるプレビュー動画

犬はその場に固定して、地面のほうを流す（＝ランニングマシン方式）。
こうすると足が地面を滑っていないかが一目で分かる。
"""
from PIL import Image, ImageDraw
import glob, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_cutout as R

FPS, SEC = 30, 5
W, H = 760, 380
STRIDE = 49.0
SPEED = STRIDE * FPS / R.N_FRAMES      # 足が滑らない速さ（px/秒）
frames = [Image.open(p).convert("RGBA") for p in sorted(glob.glob("frames_rig/r*.png"))]
FW, FH = frames[0].size
BASELINE, GROUND = 285, 330
TICK = 40

tmp = "_prev"; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
for i in range(FPS * SEC):
    t = i / FPS
    im = Image.new("RGB", (W, H), (240, 242, 238))
    d = ImageDraw.Draw(im)
    d.line([(0, GROUND), (W, GROUND)], fill=(140, 146, 138), width=3)
    off = int(SPEED * t) % TICK
    for gx in range(-off, W, TICK):      # 目盛りが流れる = 進んでいる量
        d.line([(gx, GROUND), (gx, GROUND + 12)], fill=(175, 182, 172), width=2)
    dog = frames[i % len(frames)]
    im.paste(dog, ((W - FW) // 2, GROUND - BASELINE), dog)
    im.save(f"{tmp}/p{i:04d}.png")
print(f"SPEED={SPEED:.0f}px/秒  1サイクル={R.N_FRAMES/FPS:.2f}秒  歩幅={STRIDE:.0f}px")
