#!/usr/bin/env python3
"""ねいろの「歩行コマ」を自前で作り直す（足だけ差し替え式リグ）

なぜ必要か:
  AIが描いた12コマは、実はほぼ同じ絵だった（足が動いていない）。
  そこで「胴体は元絵を使い、足だけプログラムで描いて動かす」ことにする。
  ねいろは長毛でお腹の毛が足の付け根を隠すので、この方式と相性が良い。

作り:
  1) 元絵の CUT_Y より下（＝足の部分）を消して「胴体」を作る
     切り口が定規で切ったようになるので、毛のフサフサ（フリンジ）を描き足す
  2) 4本の足を「股関節→ひざ→足先」の2関節で描く
     足先の軌道を先に決めて、ひざの位置は逆算する（IK＝インバースキネマティクス）
  3) 対角の足がペアで動く（左前＋右後ろ）＝犬の速歩（トロット）

出力: frames_rig/r00.png … （胴体の奥に遠側の足、手前に近側の足を重ねた完成コマ）
"""
from PIL import Image, ImageDraw
import math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "frames_norm", "n00.png")   # 胴体に使う元コマ
OUT = os.path.join(HERE, "frames_rig")

N_FRAMES = 16          # 1歩行サイクルのコマ数
FRINGE_SEED = 3        # 毛先のギザギザの乱数（毎回同じ形にするため固定）

# 「どの高さまで残すか」を横位置ごとに変える折れ線。(x, この高さより下は消す)
# 999 = 切らない（元の毛をそのまま残す）
#
# 【重要】元絵の4本の足は x=105〜380 の広範囲に描かれている。
# ここを消し残すと、自作の足と足して「6本足の犬」になる（実際にそうなった）。
# 一度この範囲を狭く取りすぎて失敗しているので、狭めるときは必ず
# make_body() の結果を目視すること（元の足が残っていないか）。
CUT_PROFILE = [
    (0, 999), (30, 999), (40, 240), (80, 234), (150, 230), (200, 228),
    (260, 226), (320, 226), (370, 230), (386, 236), (394, 999), (420, 999),
]

STRIDE = 56.0          # 足先が前後に動く幅(px)。1サイクルでこれだけ前に進む
LIFT = 13.0            # 足を持ち上げる高さ(px)
STANCE = 0.60          # 1サイクルのうち足が地面に着いている割合

# 色（元絵から拾った近い色）
OUTLINE = (58, 44, 36, 255)
NEAR_FILL = (250, 242, 228, 255)    # 手前側の足（クリーム色）
NEAR_SHADE = (226, 210, 188, 255)
FAR_FILL = (211, 196, 174, 255)     # 奥側の足（影で少し暗い）
FAR_SHADE = (188, 170, 148, 255)

# 4本の足の設定
#   hip    : 股関節の位置（胴体の毛に隠れる高さにする）
#   ground : 足先が地面に着く高さ
#   l1,l2  : 上腿・下腿の長さ
#   phase  : 歩行サイクルの位相（0.0 と 0.5 の対角ペア）
#   bend   : ひざの曲がる向き（+1=後ろ向き / -1=前向き）
#   near   : 手前側の足か（True なら胴体の手前に描く）
#   w1,w2  : 上腿・下腿の太さ
LEGS = [
    dict(name="後ろ・奥", hip=(132, 206), ground=277, l1=40, l2=39,
         phase=0.00, bend=-1, near=False, w1=20, w2=13, paw=(15, 9)),
    dict(name="前・奥",   hip=(295, 208), ground=276, l1=38, l2=37,
         phase=0.50, bend=+1, near=False, w1=19, w2=13, paw=(15, 9)),
    dict(name="後ろ・手前", hip=(116, 204), ground=283, l1=45, l2=44,
         phase=0.50, bend=-1, near=True,  w1=24, w2=15, paw=(18, 11)),
    dict(name="前・手前", hip=(306, 206), ground=283, l1=44, l2=43,
         phase=0.00, bend=+1, near=True,  w1=23, w2=15, paw=(18, 11)),
]


def cut_line(x):
    """CUT_PROFILE を直線でつないで、その x での切る高さを返す"""
    for (x0, y0), (x1, y1) in zip(CUT_PROFILE, CUT_PROFILE[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / max(1, x1 - x0)
            return y0 + (y1 - y0) * t
    return CUT_PROFILE[-1][1]


def make_body(src_path):
    """元コマから足を消して「胴体」を作り、切った所だけ毛先を描き足す"""
    im = Image.open(src_path).convert("RGBA")
    W, H = im.size
    px = im.load()

    cut_cols = {}      # 実際に切った列だけ記録（毛先を描くのはここだけ）
    for x in range(W):
        cy = int(round(cut_line(x)))
        lowest = None
        for y in range(H - 1, cy - 1, -1):
            if px[x, y][3]:
                lowest = y
                break
        if lowest is None:
            continue                     # 元々そこに毛が無い＝切っていない
        cut_cols[x] = cy
        for y in range(cy, H):
            if px[x, y][3]:
                px[x, y] = (0, 0, 0, 0)

    # --- 切り口に毛先を描き足す（定規で切ったような直線を隠す） ---
    rnd = random.Random(FRINGE_SEED)
    d = ImageDraw.Draw(im)
    for x, cy in cut_cols.items():
        base = px[x, cy - 2] if cy >= 2 else (0, 0, 0, 0)
        if base[3] < 200:
            continue
        length = rnd.randint(2, 8)
        col = (base[0], base[1], base[2], 255)
        d.line([(x, cy - 2), (x + rnd.randint(-1, 1), cy - 2 + length)],
               fill=col, width=1)
        if rnd.random() < 0.08:      # ときどき暗い毛筋を混ぜて毛っぽく
            d.line([(x, cy - 3), (x + rnd.randint(-1, 1), cy - 3 + max(1, length - 2))],
                   fill=(120, 100, 84, 190), width=1)
    return im


def solve_knee(hip, foot, l1, l2, bend):
    """股関節と足先の位置から、ひざの位置を逆算する（2関節のIK）

    2つの円（股関節中心・半径l1／足先中心・半径l2）の交点がひざ。
    交点は2つあるので bend でどちらに曲げるかを選ぶ。
    """
    hx, hy = hip
    fx, fy = foot
    dx, dy = fx - hx, fy - hy
    d = math.hypot(dx, dy)
    d = max(1e-3, min(d, l1 + l2 - 0.5))     # 届かない距離は伸ばしきりに丸める
    ux, uy = dx / max(d, 1e-6), dy / max(d, 1e-6)
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    bx, by = hx + ux * a, hy + uy * a
    return (bx - uy * h * bend, by + ux * h * bend)


def ankle_pos(leg, p):
    """位相 p(0〜1) における足首の位置と、足の裏の傾き(ラジアン)を返す

    足首＝すねの下端。ここから前方へ「肉球」を描く。
    接地中は足の裏が水平、宙に浮いている間だけ少しつま先が下がる。
    """
    hx, _ = leg["hip"]
    _, ph = leg["paw"]
    gy = leg["ground"] - ph / 2       # 足首は肉球の厚みぶん上
    half = STRIDE / 2
    if p < STANCE:
        # 接地中: 体に対して後ろへ流れる（＝地面を蹴っている）
        u = p / STANCE
        return (hx + half - STRIDE * u, gy), 0.0
    # 遊脚中: 前へ振り出しながら持ち上げる
    u = (p - STANCE) / (1 - STANCE)
    lift = LIFT * math.sin(math.pi * u)
    tilt = 0.45 * math.sin(math.pi * u)      # つま先が少し下を向く
    return (hx - half + STRIDE * u, gy - lift), tilt


def draw_leg(d, leg, p):
    fill, shade = (NEAR_FILL, NEAR_SHADE) if leg["near"] else (FAR_FILL, FAR_SHADE)
    hip = leg["hip"]
    ankle, tilt = ankle_pos(leg, p)
    knee = solve_knee(hip, ankle, leg["l1"], leg["l2"], leg["bend"])
    pw, ph = leg["paw"]
    # 肉球は足首から前方（右向き）へ伸ばす。tilt でつま先を下げる
    toe = (ankle[0] + pw * math.cos(tilt), ankle[1] + pw * math.sin(tilt))

    # 輪郭 → 塗り の順に太さを変えて重ねると、線画っぽい見た目になる
    for add, color in ((3, OUTLINE), (0, fill)):
        d.line([hip, knee], fill=color, width=leg["w1"] + add, joint="curve")
        d.line([knee, ankle], fill=color, width=leg["w2"] + add, joint="curve")
        d.line([ankle, toe], fill=color, width=ph + add, joint="curve")
        for pt, w in ((knee, leg["w1"]), (ankle, leg["w2"]), (toe, ph)):
            r = (w + add) / 2
            d.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=color)

    # 肉球の下側に細い影を入れて立体感を出す（太いと「シール」に見えるので細く）
    sx, sy = (toe[0] - ankle[0]) * 0.25, (toe[1] - ankle[1]) * 0.25
    d.line([(ankle[0] + sx, ankle[1] + sy + ph * 0.22),
            (toe[0] - sx * 0.5, toe[1] - sy * 0.5 + ph * 0.22)],
           fill=shade, width=max(2, ph // 3))


def body_bottom_map(body):
    """列ごとに「胴体のいちばん下の毛の位置」を調べる

    足はすべて胴体より奥にあるので、この線より上に足が見えてはいけない。
    （見えると、毛の脇から足の付け根がニョキッと生える）
    """
    W, H = body.size
    px = body.load()
    bottom = [-1] * W
    for x in range(W):
        for y in range(H - 1, -1, -1):
            if px[x, y][3] > 8:
                bottom[x] = y
                break
    return bottom


def main():
    body = make_body(SRC)
    W, H = body.size
    bottom = body_bottom_map(body)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".png"):
            os.remove(os.path.join(OUT, f))

    for i in range(N_FRAMES):
        p = i / N_FRAMES
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # 足は4本とも「胴体より奥」に描く。
        # こうすると足の付け根が胴体の毛で自然に隠れる（切り口が出ない）。
        # 奥側の2本 → 手前側の2本 の順に重ねて前後関係を出す。
        legs_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(legs_layer)
        for leg in sorted(LEGS, key=lambda L: L["near"]):
            draw_leg(dl, leg, (p + leg["phase"]) % 1.0)

        # 胴体の毛の下端より上にはみ出した足を消す
        lp = legs_layer.load()
        for x in range(W):
            for y in range(min(bottom[x] + 1, H)):
                if lp[x, y][3]:
                    lp[x, y] = (0, 0, 0, 0)

        canvas.alpha_composite(legs_layer)
        canvas.alpha_composite(body)
        canvas.save(os.path.join(OUT, f"r{i:02d}.png"))

    print(f">>> {N_FRAMES}コマ生成 -> frames_rig/  (1サイクルで {STRIDE:.0f}px 前進)")


if __name__ == "__main__":
    main()
