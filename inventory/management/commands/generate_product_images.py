import os
import random
import textwrap
from io import BytesIO
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
from catalog.models import Product, ProductImage


PALETTES = [
    ('#6366f1', '#818cf8', '#c7d2fe'),
    ('#ec4899', '#f472b6', '#fbcfe8'),
    ('#10b981', '#34d399', '#a7f3d0'),
    ('#f59e0b', '#fbbf24', '#fde68a'),
    ('#06b6d4', '#22d3ee', '#a5f3fc'),
    ('#8b5cf6', '#a78bfa', '#ddd6fe'),
    ('#ef4444', '#f87171', '#fecaca'),
    ('#14b8a6', '#2dd4bf', '#99f6e4'),
    ('#f97316', '#fb923c', '#fed7aa'),
    ('#3b82f6', '#60a5fa', '#bfdbfe'),
]


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ''
    for word in words:
        test = f'{current} {word}'.strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_image(product_name, category_name, size=(512, 512)):
    palette = random.choice(PALETTES)
    bg_color = palette[0]
    accent = palette[1]
    light = palette[2]

    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)

    draw.ellipse([-100, -100, 260, 260], fill=accent)
    draw.ellipse([260, 260, 620, 620], fill=accent)
    draw.rectangle([0, 400, 512, 512], fill=light)

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except (OSError, IOError):
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    lines = wrap_text(product_name, font_large, 420, draw)
    line_height = 36
    total_h = len(lines) * line_height
    y_start = (512 - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_large)
        tw = bbox[2] - bbox[0]
        draw.text(((512 - tw) / 2, y_start + i * line_height), line, fill='white', font=font_large)

    if category_name:
        bbox2 = draw.textbbox((0, 0), category_name, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        draw.text(((512 - tw2) / 2, y_start + len(lines) * line_height + 10), category_name, fill=light, font=font_small)

    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=90)
    return buffer.getvalue()


class Command(BaseCommand):
    help = 'Generate placeholder images for products'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Regenerate all images (delete existing)')

    def handle(self, *args, **options):
        force = options['force']
        products = Product.objects.filter(is_active=True, is_published=True).prefetch_related('images')
        created = 0
        for p in products:
            if p.images.exists() and not force:
                continue
            if force and p.images.exists():
                for img in p.images.all():
                    img.image.delete(save=False)
                    img.delete()
            image_data = generate_image(p.name, p.category.name if p.category else '')
            filename = f"{p.sku}.jpg"
            pi = ProductImage(product=p, is_primary=True, order=0)
            pi.image.save(filename, ContentFile(image_data), save=True)
            created += 1
            self.stdout.write(f'  Created image for {p.sku}: {p.name}')

        self.stdout.write(self.style.SUCCESS(f'\nDone! Created {created} product images.'))
