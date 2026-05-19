from PIL import Image
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
DST = SRC.with_suffix('.ico')

if not SRC.exists():
    print(f"Place your source image at {SRC} (PNG recommended, square, >=256x256)")
    raise SystemExit(1)

img = Image.open(SRC)
# ensure RGBA
img = img.convert('RGBA')
# save as .ico with multiple sizes
img.save(DST, sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print(f"Created icon: {DST}")
