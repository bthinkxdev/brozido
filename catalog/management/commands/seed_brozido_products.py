"""
Seed a starter BROZIDO clothing catalog: categories, products, colour variants
and a placeholder photo for each.

Idempotent — safe to re-run. Matches on category/product slug, so it only fills
in what's missing; it never touches a category or product that already exists.

Usage:
    python manage.py seed_brozido_products
"""

from __future__ import annotations

import io
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Category, Product, ProductImage, ProductVariant

# (name, slug, display_order)
CATEGORIES = [
    ("T-Shirts", "t-shirts", 1),
    ("Pants", "pants", 2),
    ("Hoodies", "hoodies", 3),
    ("Jackets", "jackets", 4),
    ("Activewear", "activewear", 5),
    ("Accessories", "accessories", 6),
]

# (name, category_slug, base_price, mrp, hsn_code, stock, colours, flags)
# flags: featured, bestseller, new_arrival
PRODUCTS = [
    ("Oversized Core Tee - Black", "t-shirts", 799, 899, "6109", 25, ("Black", "White", "Grey"), (True, False, False)),
    ("Classic Polo Tee - White", "t-shirts", 899, 1199, "6109", 20, ("White", "Navy", "Black"), (True, False, False)),
    ("Graphic Print Tee - Charcoal", "t-shirts", 899, 999, "6109", 18, ("Charcoal", "Black"), (False, False, True)),
    ("Essential Crew Tee - Olive", "t-shirts", 699, 899, "6109", 22, ("Olive", "Beige", "Black"), (False, True, False)),
    ("Oversized Tee - Sand", "t-shirts", 799, 999, "6109", 20, ("Sand", "Black", "White"), (False, False, True)),
    ("Relaxed Fit Track Pant - Beige", "pants", 1299, 1699, "6203", 18, ("Beige", "Black", "Grey"), (True, False, False)),
    ("Cargo Pants - Khaki", "pants", 1499, 1999, "6203", 15, ("Khaki", "Black", "Olive"), (False, True, False)),
    ("Wide Leg Pants - Brown", "pants", 1399, 1799, "6203", 15, ("Brown", "Black", "Beige"), (False, False, True)),
    ("Piping Track Pants - Grey", "pants", 1299, 1699, "6203", 20, ("Grey", "Black", "Navy"), (True, False, False)),
    ("Urban Hoodie - Black", "hoodies", 1599, 1999, "6110", 18, ("Black", "Grey", "Olive"), (True, False, False)),
    ("Zip-Up Hoodie - Grey", "hoodies", 1599, 2099, "6110", 16, ("Grey", "Black", "Navy"), (False, True, False)),
    ("Minimal Hoodie - Cream", "hoodies", 1699, 1999, "6110", 15, ("Cream", "Black", "Brown"), (False, False, True)),
    ("Graphic Hoodie - Navy", "hoodies", 1799, 2199, "6110", 14, ("Navy", "Black"), (False, False, True)),
    ("Bomber Jacket - Black", "jackets", 2499, 2999, "6201", 12, ("Black", "Olive"), (True, False, False)),
    ("Denim Jacket - Blue", "jackets", 2999, 3499, "6201", 10, ("Blue", "Black"), (False, True, False)),
    ("Windbreaker Jacket - Olive", "jackets", 2299, 2799, "6201", 12, ("Olive", "Black", "Grey"), (False, False, True)),
    ("Athleisure Set - Navy", "activewear", 2499, 2999, "6112", 14, ("Navy", "Black", "Grey"), (False, True, False)),
    ("Training Tee - Grey Melange", "activewear", 799, 999, "6112", 20, ("Grey", "Black"), (False, False, True)),
    ("Signature Cap - Black", "accessories", 599, 799, "6505", 30, ("Black", "Olive", "White"), (False, False, True)),
    ("Canvas Tote Bag - Beige", "accessories", 899, 1199, "4202", 16, ("Beige", "Black"), (False, False, False)),
]

# One soft tone per category, cycled per product so the placeholder gallery reads as a set.
TONES = {
    "t-shirts": [(214, 209, 199), (222, 217, 208), (196, 190, 180)],
    "pants": [(206, 200, 190), (190, 184, 174), (200, 194, 184)],
    "hoodies": [(160, 160, 158), (172, 172, 168), (150, 148, 145)],
    "jackets": [(150, 148, 145), (140, 138, 136), (130, 128, 126)],
    "activewear": [(185, 180, 172), (170, 166, 158), (196, 190, 180)],
    "accessories": [(170, 160, 150), (180, 172, 162), (160, 152, 142)],
}


def _placeholder_image(*, label: str, tone: tuple[int, int, int]) -> ContentFile:
    """A soft-tone JPEG with a dark garment silhouette and the product name — a stand-in
    until real product photography is uploaded from Content -> Products."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 900, 1200
    im = Image.new("RGB", (width, height), tone)
    draw = ImageDraw.Draw(im)
    draw.rectangle((width * 0.3, height * 0.18, width * 0.7, height * 0.85), fill=(30, 30, 30))
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    draw.text((width * 0.05, height * 0.9), label, fill=(90, 90, 90), font=font)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Seed a starter BROZIDO clothing catalog (categories, products, variants, placeholder photos)."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {}
        for name, slug, order in CATEGORIES:
            category, created = Category.objects.get_or_create(
                slug=slug, defaults={"name": name, "display_order": order, "is_active": True}
            )
            categories[slug] = category
            self.stdout.write(f"{'Created' if created else 'Already exists'} category: {name}")

        created_count = 0
        for name, cat_slug, price, mrp, hsn, stock, colours, (featured, bestseller, new_arrival) in PRODUCTS:
            slug = name.lower().replace(" - ", "-").replace(" ", "-").replace("/", "-")
            if Product.objects.filter(slug=slug).exists():
                self.stdout.write(f"Already exists product: {name}")
                continue

            sku = f"BRZ-{slug.upper()[:24]}"
            product = Product.objects.create(
                name=name,
                slug=slug,
                sku=sku,
                category=categories[cat_slug],
                base_price=Decimal(price),
                mrp=Decimal(mrp),
                hsn_code=hsn,
                stock_quantity=0,  # sold through the colour variants below
                is_active=True,
                is_featured=featured,
                is_bestseller=bestseller,
                is_new_arrival=new_arrival,
            )

            tone = TONES[cat_slug][created_count % len(TONES[cat_slug])]
            image = ProductImage(product=product, is_primary=True, alt_text=name, display_order=0)
            image.image.save(f"{slug}.jpg", _placeholder_image(label=name, tone=tone), save=True)

            per_colour_stock = max(stock // len(colours), 1)
            for i, colour in enumerate(colours):
                ProductVariant.objects.create(
                    product=product,
                    variant_type="colour",
                    name=colour,
                    sku_suffix=colour[:3].upper(),
                    stock_quantity=per_colour_stock,
                )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"Created product: {name} ({len(colours)} colours)"))

        self.stdout.write(self.style.SUCCESS(f"Done. {created_count} new product(s) created."))
