"""Create icon from logo."""
import shutil
from PIL import Image
import os

# Source and destination paths
source = r"C:\Users\alnen\Downloads\Platinum zenith Novi Logo (644 x 200 px) (1000 x 1000 px).png"
dest_png = r"C:\Users\alnen\Desktop\Niwa Ai Voice imput\assets\logo.png"
dest_ico = r"C:\Users\alnen\Desktop\Niwa Ai Voice imput\assets\icon.ico"

# Create assets folder if it doesn't exist
os.makedirs(r"C:\Users\alnen\Desktop\Niwa Ai Voice imput\assets", exist_ok=True)

# Copy PNG logo
print(f"Copying logo from {source} to {dest_png}")
shutil.copy2(source, dest_png)
print("Logo copied OK")

# Create ICO file
print("Creating icon...")
img = Image.open(dest_png)

# ICO files need multiple sizes
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img_resized = []

for size in sizes:
    img_copy = img.copy()
    img_copy.thumbnail(size, Image.Resampling.LANCZOS)
    img_resized.append(img_copy)

# Save as .ico
img_resized[0].save(dest_ico, format='ICO', sizes=sizes)
print(f"Icon created: {dest_ico}")
print("\nDone!")
