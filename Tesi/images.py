import colorsys
from PIL import Image, ImageDraw
import random
import os
import math

def random_color():
    h = random.random()
    s = 1
    v = 1
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))

def create_image(filename, size=(100, 100)):
    img = Image.new('RGB', size, random_color())
    draw = ImageDraw.Draw(img)
    for _ in range(10):
        shape_type = random.choice(['rectangle', 'ellipse', 'line', 'triangle', 'polygon'])
        color = random_color()
        angle = random.uniform(0, 360)
        x0, y0 = random.randint(0, size[0]), random.randint(0, size[1])
        x1, y1 = random.randint(0, size[0]), random.randint(0, size[1])
        width = random.randint(20, 60)
        height = random.randint(20, 60)
        if shape_type == 'rectangle':
            xy = [x0, y0, x0 + width, y0 + height]
            draw.rectangle(xy, fill=color)
        elif shape_type == 'ellipse':
            xy = [x0, y0, x0 + width, y0 + height]
            draw.ellipse(xy, fill=color)
        elif shape_type == 'line':
            xy = [x0, y0, x1, y1]
            draw.line(xy, fill=color, width=5)
        elif shape_type == 'triangle':
            points = [(x0, y0), (x0 + width, y0), (x0 + width // 2, y0 - height)]
            draw.polygon(points, fill=color)
        elif shape_type == 'polygon':
            num_sides = random.randint(5, 8)
            radius = random.randint(20, 40)
            points = [(x0 + radius * math.cos(2 * math.pi * i / num_sides + math.radians(angle)),
                       y0 + radius * math.sin(2 * math.pi * i / num_sides + math.radians(angle)))
                      for i in range(num_sides)]
            draw.polygon(points, fill=color)
    img.save(filename)

os.makedirs('generated_images', exist_ok=True)

create_image('generated_images/banner.jpg', size=(300, 150))
create_image('generated_images/profile.jpg', size=(100, 100))
create_image('generated_images/streak-icon.png', size=(20, 20))
create_image('generated_images/achievement-icon.png', size=(20, 20))
create_image('generated_images/badge-icon.png', size=(20, 20))

print('success')
