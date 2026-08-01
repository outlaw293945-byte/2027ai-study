from PIL import Image, ImageDraw
import glob, sys
files = sorted(glob.glob("frames_rig/r*.png"))
step = int(sys.argv[1]) if len(sys.argv)>1 else 1
files = files[::step]
cols = 4; rows = (len(files)+cols-1)//cols
W, H = Image.open(files[0]).size
sheet = Image.new("RGB", (W*cols, H*rows), (252,252,250))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert("RGBA")
    cx, cy = (i%cols)*W, (i//cols)*H
    sheet.paste(im, (cx, cy), im)
    d.rectangle([cx,cy,cx+W-1,cy+H-1], outline=(210,210,210))
    d.text((cx+6, cy+6), f.split('/')[-1], fill=(200,0,0))
sheet.save("rig_check.png"); print(sheet.size)
