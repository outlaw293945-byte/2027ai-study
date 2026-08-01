#!/usr/bin/env python3
"""ねいろが画面を縦横無尽に歩くレイヤー（透明PNG連番）を作る

ffmpeg の式だけでは「左右反転」と「拡大縮小」を途中で切り替えられないので、
1コマずつ Python で描いて連番PNGにする。あとで ffmpeg が動画に重ねる。

考え方:
  - 1回の「お散歩」= 画面の外から入って、別の辺の外へ抜ける直線移動
  - 進む向きが左なら絵を左右反転（コマは右向きで描かれているため）
  - 画面の上のほうにいるときは小さく（遠く）、下は大きく（近く）見せる
  - 歩くコマ送りは「進んだ距離」に連動させる（足が地面を滑らない）
"""
from PIL import Image
import argparse, glob, math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser(description="ねいろが歩く透明PNG連番を作る")
ap.add_argument("--dur", type=float, required=True, help="動画の長さ（秒）")
ap.add_argument("--out", required=True, help="PNG連番の出力フォルダ")
ap.add_argument("--mode", default="random", choices=["random", "straight"],
                help="random=方向がランダム / straight=画面下を左から右へ")
ap.add_argument("--seed", type=int, default=7, help="コースの乱数の種（変えると別のコースになる）")
ap.add_argument("--width", type=int, default=1920)
ap.add_argument("--height", type=int, default=1080)
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--frames-dir", default=os.path.join(HERE, "frames_rig"),
                help="歩行コマ（r00.png…）のあるフォルダ")
args = ap.parse_args()

W, H, FPS, DUR, SEED, MODE, OUT = (args.width, args.height, args.fps,
                                   args.dur, args.seed, args.mode, args.out)

# SPEED と STRIDE は必ずセットで考える。
# 1歩(=STRIDE)で進む距離より速く動かすと、足が地面を滑って「氷の上」になる。
SPEED = 175.0        # 進む速さ（px/秒、拡大率1.0のとき）
STRIDE = 49.0        # 足のコマが1周する間に進む距離（rig_cutout.py が表示する値に合わせる）
GAP = 0.4            # お散歩と次のお散歩の間の空き（秒）
SCALE_TOP = 0.85     # 画面の上を歩くときの大きさ
SCALE_BOTTOM = 1.35  # 画面の下を歩くときの大きさ

# 1080p以外のときは、犬の大きさと速さを画面の高さに合わせて縮める
RES = H / 1080.0
SPEED *= RES
SCALE_TOP *= RES
SCALE_BOTTOM *= RES

random.seed(SEED)
paths = sorted(glob.glob(os.path.join(args.frames_dir, "r*.png")))
if not paths:
    raise SystemExit(f"!! 歩行コマが見つかりません: {args.frames_dir}/r*.png")
frames = [Image.open(p).convert("RGBA") for p in paths]
flipped = [f.transpose(Image.FLIP_LEFT_RIGHT) for f in frames]
FW, FH = frames[0].size          # 420x300
FEET = 285                        # コマの中での足元の位置

os.makedirs(OUT, exist_ok=True)
for old in glob.glob(f"{OUT}/*.png"):
    os.remove(old)


def edge_point(side, margin):
    """画面の外側のどこか1点を返す（margin ぶん外に出す）"""
    if side == "left":
        return -margin, random.uniform(H * 0.30, H * 0.95)
    if side == "right":
        return W + margin, random.uniform(H * 0.30, H * 0.95)
    if side == "top":
        return random.uniform(W * 0.10, W * 0.90), -margin
    return random.uniform(W * 0.10, W * 0.90), H + margin   # bottom


# 画面外に出しきるための余白（大きく映るときの犬の幅ぶん）
MARGIN = int(FW * SCALE_BOTTOM * 0.6) + 20

SIDES = ["left", "right", "top", "bottom"]
trips = []          # (開始秒, 終了秒, 始点, 終点)
t = 0.0
while t < DUR:
    if MODE == "straight":
        # 画面下を左から右へ、まっすぐ何度も通る（最初に作ったのと同じ動き）
        gy = H * 0.93
        p0, p1 = (-float(MARGIN), gy), (W + float(MARGIN), gy)
        gap = 0.0
    else:
        side_a = random.choice(SIDES)
        side_b = random.choice([s for s in SIDES if s != side_a])
        p0 = edge_point(side_a, MARGIN)
        p1 = edge_point(side_b, MARGIN)
        gap = GAP
    dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    dt = dist / SPEED
    trips.append((t, t + dt, p0, p1))
    t += dt + gap

n_frames = int(DUR * FPS) + 1
for i in range(n_frames):
    tt = i / FPS
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    for (t0, t1, p0, p1) in trips:
        if not (t0 <= tt <= t1):
            continue
        u = (tt - t0) / (t1 - t0)
        cx = p0[0] + (p1[0] - p0[0]) * u          # 足元の中心x
        cy = p0[1] + (p1[1] - p0[1]) * u          # 足元のy
        dx = p1[0] - p0[0]

        # 高さに応じた遠近の大きさ
        k = min(max(cy / H, 0.0), 1.0)
        s = SCALE_TOP + (SCALE_BOTTOM - SCALE_TOP) * k

        # 進んだ距離からコマ番号を決める（足が滑らないように）
        dist_done = math.hypot(cx - p0[0], cy - p0[1])
        idx = int(dist_done / (STRIDE * s) * len(frames)) % len(frames)

        src = (flipped if dx < 0 else frames)[idx]
        fw, fh = max(1, round(FW * s)), max(1, round(FH * s))
        dog = src.resize((fw, fh), Image.LANCZOS)

        # 上下にわずかに弾ませる
        bob = 3 * s * math.sin(2 * math.pi * (dist_done / (STRIDE * s)) * 2)
        x = round(cx - fw / 2)
        y = round(cy - FEET * s + bob)
        # paste は画面外にはみ出しても自動で切ってくれる
        canvas.paste(dog, (x, y), dog)

    canvas.save(f"{OUT}/d{i:05d}.png", compress_level=1)
    if i % 120 == 0:
        print(f"  {i}/{n_frames} コマ")

print(f">>> {n_frames}コマ生成完了 / お散歩 {len(trips)}回 -> {OUT}")
for j, (t0, t1, p0, p1) in enumerate(trips):
    d = "→" if p1[0] > p0[0] else "←"
    print(f"   {j+1}回目 {t0:5.1f}〜{t1:5.1f}秒  ({p0[0]:.0f},{p0[1]:.0f}) {d} ({p1[0]:.0f},{p1[1]:.0f})")
