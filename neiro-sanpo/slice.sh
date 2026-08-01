#!/bin/bash
# スプライトシートを1コマずつに切り分け、緑背景を透明にする
#   colorkey = 指定した色を透明にするフィルタ
#   despill  = 緑が毛に反射して緑っぽくなるのを打ち消すフィルタ
set -euo pipefail
cd "$(dirname "$0")"

SHEET="spritesheet_raw.png"
COLS=4; ROWS=3
SW=1195; SH=896          # シート全体のサイズ
INSET=6                  # マス目の境界線を避けるため内側に寄せる量

mkdir -p frames
rm -f frames/*.png

n=0
for (( r=0; r<ROWS; r++ )); do
  for (( c=0; c<COLS; c++ )); do
    x=$(( SW * c / COLS + INSET ))
    y=$(( SH * r / ROWS + INSET ))
    w=$(( SW / COLS - INSET * 2 ))
    h=$(( SH / ROWS - INSET * 2 ))
    out=$(printf "frames/f%02d.png" "$n")
    ffmpeg -hide_banner -loglevel error -y -i "$SHEET" \
      -vf "crop=${w}:${h}:${x}:${y},colorkey=0x00FF00:0.28:0.06,despill=type=green:mix=0.6" \
      -frames:v 1 "$out"
    n=$(( n + 1 ))
  done
done

echo ">>> ${n}コマ切り出し完了"
ls frames/
