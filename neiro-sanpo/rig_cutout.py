#!/usr/bin/env python3
"""ねいろの歩行コマを作る（元絵の足を切り出して振る方式）

rig_legs.py との違い:
  rig_legs.py … 足を「プログラムで描く」。形は自由だが、毛のふかふか感が出ない。
  この版      … 元絵の足を「切り出して回す」。**毛が描き込まれたまま**動かせる。

考え方:
  1) 胴体から下（＝足）を切り離す                     … rig_legs.make_body を再利用
  2) 切り離した部分を、輪郭線で囲まれたかたまりごとに4本へ分ける
     （足どうしが接触していて、横位置で機械的には切れないため）
  3) 各足を「付け根」を中心に少しだけ回す
     対角の足がペアで動く（右前＋左後ろ / 左前＋右後ろ）＝犬の速歩

出力: frames_rig/r00.png …
"""
from PIL import Image
from collections import deque
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_legs as R          # make_body / cut_line / SRC を借りる

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "frames_rig")

N_FRAMES = 16
AMP_DEG = 13.0      # 足を振る角度（片側）。元絵の右前足くらいの控えめな動きに合わせた
OUTLINE_LUM = 118   # これより暗ければ輪郭線とみなす
STEM = 24           # 足の上端を上へ伸ばす長さ。回したとき毛との間に隙間ができないように

# 4本の足の設定
#   xmax  : この横位置より左のかたまりをこの足とみなす（元絵を実測して決めた）
#   pivot : 回転の中心（＝付け根）。胴体の毛に隠れる位置にする
#   phase : 歩行サイクルの位相。対角の足を同じ位相にすると犬らしい速歩になる
#   near  : 手前側の足か（描く順の前後関係に使う）
#   copy_from : 別の足を複製して使う（元絵の形が使えないとき）
#   scale/tint: 複製したものを奥側らしく「少し小さく・少し暗く」する
LEGS = [
    dict(name="右後ろ(手前)", xmax=110, pivot=(74, 210),  phase=0.5, near=True),
    dict(name="左後ろ(奥)",   xmax=190, pivot=(138, 212), phase=0.0, near=False),
    # 元絵の左前足は肉球が後ろ向きの「折りたたんだ足」で、他の3本と向きが揃わない。
    # そのため、お手本の右前足を複製して使う。
    dict(name="左前(奥)",     xmax=260, pivot=(262, 206), phase=0.5, near=False,
         copy_from=3, scale=0.88, tint=(0.80, 0.76, 0.72)),
    dict(name="右前(手前)",   xmax=999, pivot=(272, 208), phase=0.0, near=True),
]


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def split_legs(legs_img):
    """足の画像を4本に切り分ける

    輪郭線（暗い画素）をいったん除くと、足の中身どうしが分離する。
    そのかたまりを横位置で4本に振り分け、あとから輪郭線を近い足へ吸わせる。
    """
    W, H = legs_img.size
    p = legs_img.load()
    lab = [[0] * H for _ in range(W)]      # 0=未割り当て, 1〜4=足番号

    # --- 輪郭線を除いた「中身」を、つながりごとにたどる ---
    seen = [[False] * H for _ in range(W)]
    for x0 in range(W):
        for y0 in range(H):
            c = p[x0, y0]
            if c[3] < 40 or lum(c) < OUTLINE_LUM or seen[x0][y0]:
                continue
            q = deque([(x0, y0)])
            seen[x0][y0] = True
            pix = []
            while q:
                x, y = q.popleft()
                pix.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and not seen[nx][ny]:
                        cc = p[nx, ny]
                        if cc[3] >= 40 and lum(cc) >= OUTLINE_LUM:
                            seen[nx][ny] = True
                            q.append((nx, ny))
            if len(pix) < 250:
                continue                    # ハイライト等の小さな島は後で吸収させる
            cx = sum(a for a, _ in pix) / len(pix)
            idx = next(i for i, L in enumerate(LEGS) if cx < L["xmax"])
            for a, b in pix:
                lab[a][b] = idx + 1

    # --- 輪郭線と小さな島を、隣の足へ広げて吸わせる ---
    q = deque((x, y) for x in range(W) for y in range(H) if lab[x][y])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not lab[nx][ny] and p[nx, ny][3] >= 40:
                lab[nx][ny] = lab[x][y]
                q.append((nx, ny))

    # --- 足ごとの画像に分ける。上端は STEM ぶん上へ伸ばして毛の下に潜らせる ---
    # なぜ伸ばすか: 足を回すと上端が斜めにずれ、毛との間に隙間ができるため。
    # 伸ばす色は「フチの半透明画素」ではなく必ず中身から拾う（拾い間違えると縞模様になる）。
    layers = []
    for i in range(len(LEGS)):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lp = layer.load()
        for x in range(W):
            solid = []
            for y in range(H):
                if lab[x][y] == i + 1:
                    lp[x, y] = p[x, y]
                    if p[x, y][3] > 200:
                        solid.append(y)
            if len(solid) < 6:
                continue                    # 端の細い部分は伸ばさない（ヒゲ状のゴミになる）
            top = solid[0]
            # 毛の切り口に接している列だけ伸ばす。
            # 足先（肉球）のように下の方から始まる列まで伸ばすと、
            # 毛より下に「板」がはみ出して見える（実際にそうなった）。
            if top > R.cut_line(x) + 6:
                continue
            c = p[x, solid[min(3, len(solid) - 1)]]     # 中身の色
            col = (c[0], c[1], c[2], 255)
            for y in range(max(0, top - STEM), top):
                lp[x, y] = col
        layers.append(layer)
    return layers


def duplicate_leg(src, src_pivot, dst_pivot, scale, tint):
    """ある足を複製して、別の付け根に合わせて置き直す

    元絵の足の形がそのまま使えないとき用。
    奥側の足に見せるため、少し小さくして色を暗く落とす。
    """
    bb = src.getbbox()
    sub = src.crop(bb)
    sub = sub.resize((max(1, round(sub.width * scale)),
                      max(1, round(sub.height * scale))), Image.LANCZOS)
    sp = sub.load()
    for x in range(sub.width):
        for y in range(sub.height):
            r, g, b, a = sp[x, y]
            if a:
                sp[x, y] = (int(r * tint[0]), int(g * tint[1]), int(b * tint[2]), a)

    # 付け根から見た相対位置を保ったまま、新しい付け根の位置へ置く
    ox, oy = bb[0] - src_pivot[0], bb[1] - src_pivot[1]
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    out.paste(sub, (round(dst_pivot[0] + ox * scale),
                    round(dst_pivot[1] + oy * scale)), sub)
    return out


def foot_travel(layer, pivot):
    """この足の「足先」が1往復で動く距離。歩幅として使う"""
    bbox = layer.getbbox()
    if not bbox:
        return 0.0
    # 足先＝付け根からいちばん遠い点、で近似する
    far = math.hypot(max(abs(bbox[0] - pivot[0]), abs(bbox[2] - pivot[0])),
                     bbox[3] - pivot[1])
    return 2 * math.sin(math.radians(AMP_DEG)) * far


def main():
    body = R.make_body(R.SRC)
    W, H = body.size

    orig = Image.open(R.SRC).convert("RGBA")
    op = orig.load()
    legs_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lp = legs_img.load()
    for x in range(W):
        cy = int(round(R.cut_line(x)))
        for y in range(cy, H):
            if op[x, y][3]:
                lp[x, y] = op[x, y]

    layers = split_legs(legs_img)

    # 元絵の形が使えない足を、別の足の複製に差し替える
    for i, L in enumerate(LEGS):
        if "copy_from" in L:
            src_i = L["copy_from"]
            layers[i] = duplicate_leg(layers[src_i], LEGS[src_i]["pivot"],
                                      L["pivot"], L["scale"], L["tint"])

    for L, layer in zip(LEGS, layers):
        bb = layer.getbbox()
        src = f"（{LEGS[L['copy_from']]['name']}の複製）" if "copy_from" in L else ""
        print(f"  {L['name']}: {'OK' if bb else '!! 空っぽ'}  範囲={bb} {src}")

    stride = max(foot_travel(l, L["pivot"]) for l, L in zip(layers, LEGS))

    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".png"):
            os.remove(os.path.join(OUT, f))

    # 胴体の毛の下端。足はすべてこの線より下にだけ見えるようにする
    bottom = R.body_bottom_map(body)

    for i in range(N_FRAMES):
        t = i / N_FRAMES
        # 足はすべて胴体より奥。手前側の足を後に重ねて前後関係を出す
        legs_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for want_near in (False, True):
            for L, layer in zip(LEGS, layers):
                if L["near"] != want_near:
                    continue
                ang = AMP_DEG * math.sin(2 * math.pi * (t + L["phase"]))
                legs_layer.alpha_composite(
                    layer.rotate(ang, resample=Image.BICUBIC, center=L["pivot"]))

        # 毛の下端より上へはみ出した足（＝継ぎ足した根元や回転でずれた分）を消す
        lp2 = legs_layer.load()
        for x in range(W):
            for y in range(min(bottom[x] + 1, H)):
                if lp2[x, y][3]:
                    lp2[x, y] = (0, 0, 0, 0)

        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        canvas.alpha_composite(legs_layer)
        canvas.alpha_composite(body)
        canvas.save(os.path.join(OUT, f"r{i:02d}.png"))

    print(f">>> {N_FRAMES}コマ生成 -> frames_rig/  (1サイクルで約 {stride:.0f}px 前進)")
    print(f"    ※ make_dog_layer.py の STRIDE を {stride:.0f} に合わせること")


if __name__ == "__main__":
    main()
