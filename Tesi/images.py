import colorsys
from PIL import Image, ImageDraw
import random
import os
import math

def bright_random_color():
    h = random.random()
    s = 1
    v = 1
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))

def create_image(filename, size=(300, 300)):
    img = Image.new('RGB', size, bright_random_color())
    draw = ImageDraw.Draw(img)
    for _ in range(20):
        shape_type = random.choice(['rectangle', 'ellipse', 'line', 'triangle', 'polygon'])
        color = bright_random_color()
        x0, y0 = random.randint(0, size[0]), random.randint(0, size[1])
        x1, y1 = random.randint(0, size[0]), random.randint(0, size[1])
        width = random.randint(40, 120)
        height = random.randint(40, 120)
        if shape_type == 'rectangle':
            draw.rectangle([x0, y0, x0 + width, y0 + height], fill=color)
        elif shape_type == 'ellipse':
            draw.ellipse([x0, y0, x0 + width, y0 + height], fill=color)
        elif shape_type == 'line':
            draw.line([x0, y0, x1, y1], fill=color, width=10)
        elif shape_type == 'triangle':
            points = [(x0, y0), (x0 + width, y0), (x0 + width // 2, y0 - height)]
            draw.polygon(points, fill=color)
        elif shape_type == 'polygon':
            num_sides = random.randint(5, 8)
            radius = random.randint(40, 80)
            points = [(x0 + radius * math.cos(2 * math.pi * i / num_sides),
                       y0 + radius * math.sin(2 * math.pi * i / num_sides))
                      for i in range(num_sides)]
            draw.polygon(points, fill=color)
    img.save(filename)

def create_banner_image(filename, size=(1200, 600)):
    img = Image.new('RGB', size, bright_random_color())
    draw = ImageDraw.Draw(img)
    for _ in range(30):
        shape_type = random.choice(['rectangle', 'ellipse', 'triangle', 'polygon'])
        color = bright_random_color()
        x0, y0 = random.randint(0, size[0] - 100), random.randint(0, size[1] - 100)
        width, height = random.randint(50, 100), random.randint(50, 100)
        if shape_type == 'rectangle':
            draw.rectangle([x0, y0, x0 + width, y0 + height], fill=color)
        elif shape_type == 'ellipse':
            draw.ellipse([x0, y0, x0 + width, y0 + height], fill=color)
        elif shape_type == 'triangle':
            points = [(x0, y0), (x0 + width, y0), (x0 + width // 2, y0 - height)]
            draw.polygon(points, fill=color)
        elif shape_type == 'polygon':
            num_sides = random.randint(5, 8)
            radius = random.randint(25, 50)
            points = [(x0 + radius * math.cos(2 * math.pi * i / num_sides),
                       y0 + radius * math.sin(2 * math.pi * i / num_sides))
                      for i in range(num_sides)]
            draw.polygon(points, fill=color)
    img.save(filename)

def create_unique_shape_image(filename, size=(400, 400)):
    img = Image.new('RGB', size, bright_random_color())
    draw = ImageDraw.Draw(img)
    shape_type = random.choice(['rectangle', 'ellipse', 'triangle', 'polygon'])
    color = bright_random_color()
    x0, y0 = size[0] // 4, size[1] // 4
    width, height = size[0] // 2, size[1] // 2
    if shape_type == 'rectangle':
        draw.rectangle([x0, y0, x0 + width, y0 + height], fill=color)
    elif shape_type == 'ellipse':
        draw.ellipse([x0, y0, x0 + width, y0 + height], fill=color)
    elif shape_type == 'triangle':
        points = [(x0, y0), (x0 + width, y0), (x0 + width // 2, y0 - height)]
        draw.polygon(points, fill=color)
    elif shape_type == 'polygon':
        num_sides = random.randint(5, 8)
        radius = min(width, height) // 2
        points = [(x0 + size[0] // 2 + radius * math.cos(2 * math.pi * i / num_sides),
                   y0 + size[1] // 2 + radius * math.sin(2 * math.pi * i / num_sides))
                  for i in range(num_sides)]
        draw.polygon(points, fill=color)
    img.save(filename)

os.makedirs('generated_images', exist_ok=True)

create_banner_image('generated_images/banner.jpg', size=(1200, 600))
create_unique_shape_image('generated_images/profile.jpg', size=(400, 400))
create_image('generated_images/streak-icon.png', size=(80, 80))
create_image('generated_images/achievement-icon.png', size=(80, 80))
create_image('generated_images/badge-icon.png', size=(80, 80))

