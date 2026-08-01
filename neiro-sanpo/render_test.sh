#!/bin/bash
# ねいろの散歩つき音楽動画（テスト版）
#
# 入力は3つ:
#   0 = ジャケット画像（静止画をループ）
#   1 = 曲
#   2 = ねいろの歩行コマ（連番PNGをパラパラ漫画として読む）
set -euo pipefail
cd "$(dirname "$0")"

AUDIO="../any/Hello World.mp3"
IMAGE="../any/Hello World.jpeg"
OUT="test_dog.mp4"

W=1920; H=1080; FPS=30
WALK_FPS=12          # 歩行アニメのコマ送り速度（1秒に12コマ）
DOG_W=350            # 画面上でのねいろの大きさ（キャンバス幅）
DOG_H=250
FEET=237             # 上のサイズにしたときの「足元」の位置
BASE_Y=1020          # 画面上で足を着ける高さ
SPEED=260            # 横移動の速さ（px/秒）
WAVE_H=$(( H / 6 ))

DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$AUDIO")
W2=$(( W * 4 / 3 )); H2=$(( H * 4 / 3 ))
TOTAL_FRAMES=$(awk "BEGIN{printf \"%d\", $DUR * $FPS}")
ZRATE=$(awk "BEGIN{printf \"%.8f\", 0.12 / $TOTAL_FRAMES}")
TRAVEL=$(( W + DOG_W ))          # 画面外→画面外までの移動距離
OY=$(( BASE_Y - FEET ))          # overlayのy座標（左上基準なので足元から逆算）

FC="\
[0:v]scale=${W2}:${H2}:force_original_aspect_ratio=increase,crop=${W2}:${H2},gblur=sigma=30[bg];\
[0:v]scale=${W2}:${H2}:force_original_aspect_ratio=decrease[fg];\
[bg][fg]overlay=(W-w)/2:(H-h)/2[still];\
[still]zoompan=z='min(1+${ZRATE}*on,1.12)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${W}x${H}:fps=${FPS}[vid];\
[1:a]asplit=2[a_out][a_wave];\
[a_wave]showwaves=s=${W}x${WAVE_H}:mode=cline:rate=${FPS}:scale=sqrt:colors=white|white[wf];\
[wf]pad=${W}:${H}:0:${H}-${WAVE_H}:black,format=gbrp[wavefull];\
[vid]drawbox=x=0:y=ih-${WAVE_H}:w=iw:h=${WAVE_H}:color=black@0.40:t=fill,format=gbrp[vidbar];\
[vidbar][wavefull]blend=all_mode=screen,format=yuva420p[base];\
[2:v]scale=${DOG_W}:${DOG_H}[dog];\
[base][dog]overlay=x='mod(t*${SPEED}\,${TRAVEL})-${DOG_W}':y='${OY}+6*sin(2*PI*t*2)':eval=frame:format=auto[v]"

echo ">>> 作成中… 長さ=${DUR%.*}秒"
ffmpeg -hide_banner -loglevel warning -stats -y \
  -loop 1 -framerate "$FPS" -t "$DUR" -i "$IMAGE" \
  -i "$AUDIO" \
  -framerate "$WALK_FPS" -loop 1 -t "$DUR" -i "frames_norm/n%02d.png" \
  -filter_complex "$FC" \
  -map "[v]" -map "[a_out]" \
  -c:v libx264 -preset veryfast -crf 23 -g $(( FPS * 2 )) \
  -c:a aac -b:a 256k \
  -shortest -movflags +faststart "$OUT"

echo ">>> 完了: $OUT"
ls -lh "$OUT" | awk '{print "   サイズ:", $5}'
