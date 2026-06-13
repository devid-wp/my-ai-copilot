import math, os
from PIL import Image, ImageDraw

size = 256
img = Image.new("RGBA", (size, size), (0,0,0,0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([8,8,248,248], radius=52, fill="#7c3aed")
cx, cy, r = 128, 128, 78
pts = [(cx + r*math.cos(math.radians(-90+60*i)),
        cy + r*math.sin(math.radians(-90+60*i))) for i in range(6)]
draw.polygon(pts, outline="white", fill=None, width=12)
r2 = 50
pts2 = [(cx + r2*math.cos(math.radians(-90+60*i)),
         cy + r2*math.sin(math.radians(-90+60*i))) for i in range(6)]
draw.polygon(pts2, outline="white", fill=None, width=5)

base_dir = os.path.dirname(os.path.abspath(__file__))
png_path = os.path.join(base_dir, "icon.png")
ico_path = os.path.join(base_dir, "icon.ico")

img.save(png_path)
print("Saved: icon.png")

# Сохранить также как ICO для Windows
img.save(ico_path, format="ICO", sizes=[(32, 32), (64, 64), (128, 128), (256, 256)])
print("Saved: icon.ico")
