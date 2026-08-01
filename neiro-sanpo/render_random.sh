#!/bin/bash
# ねいろの散歩つき音楽動画を作る（共通スクリプト）
#   使い方: ./render_random.sh <PNG連番フォルダ> <出力ファイル名>
#   入力3 = make_dog_layer.py が作った透明PNG連番（位置・反転・大小は計算済み）
set -euo pipefail
cd "$(dirname "$0")"

AUDIO="../any/Hello World.mp3"
IMAGE="../any/Hello World.jpeg"
LAYER="${1:-dog_layer}"
OUT="${2:-test_dog_random.mp4}"

W=1920; H=1080; FPS=30
WAVE_H=$(( H / 6 ))

DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$AUDIO")
W2=$(( W * 4 / 3 )); H2=$(( H * 4 / 3 ))
TOTAL_FRAMES=$(awk "BEGIN{printf \"%d\", $DUR * $FPS}")
ZRATE=$(awk "BEGIN{printf \"%.8f\", 0.12 / $TOTAL_FRAMES}")

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
[base][2:v]overlay=0:0:format=auto,format=yuv420p[v]"

echo ">>> 作成中… 長さ=${DUR%.*}秒  素材=$LAYER  出力=$OUT"
ffmpeg -hide_banner -loglevel warning -stats -y \
  -loop 1 -framerate "$FPS" -t "$DUR" -i "$IMAGE" \
  -i "$AUDIO" \
  -framerate "$FPS" -i "$LAYER/d%05d.png" \
  -filter_complex "$FC" \
  -map "[v]" -map "[a_out]" \
  -c:v libx264 -preset veryfast -crf 23 -g $(( FPS * 2 )) \
  -c:a aac -b:a 256k \
  -shortest -movflags +faststart "$OUT"

echo ">>> 完了: $OUT"
ls -lh "$OUT" | awk '{print "   サイズ:", $5}'
