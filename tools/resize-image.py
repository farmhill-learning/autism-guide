"""Script to resize an image
"""
from PIL import Image
import argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("-W", "--width", type=int, help="set the width of the image")
p.add_argument("-H", "--height", type=int, help="set the height of the image")
p.add_argument("-o", "--output", help="path to save the resized image (default: output.png)", default="output.png")
p.add_argument("image_file", help="image file to resize")
args = p.parse_args()

image = Image.open(args.image_file)

w = args.width or image.width
h = args.height or image.height

image.thumbnail((w, h))
image.save(args.output)

path = Path(args.output)
image_size = path.stat().st_size // 1024

print("Saved the resized image to", args.output)
print("Image size:", image.size)
print(f"File size: {image_size} KB")

