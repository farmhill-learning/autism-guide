from PIL import Image

img = Image.open("images/smiley_empty_chart.jpg")
print(img.size)
img.thumbnail((400, 400))
img.save("images/smiley_empty_chart_400.png")