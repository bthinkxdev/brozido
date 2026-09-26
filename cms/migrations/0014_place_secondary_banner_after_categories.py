"""Move the secondary banner from the bottom of the homepage to just after Shop by Category."""

from django.db import migrations


def place_after_categories(apps, schema_editor):
    HomepageSection = apps.get_model("cms", "HomepageSection")
    categories = HomepageSection.objects.filter(section_type="shop_by_category").first()
    banner = HomepageSection.objects.filter(section_type="secondary_banner").first()
    if categories is None or banner is None:
        return
    if banner.display_order > categories.display_order + 1:
        banner.display_order = categories.display_order + 1
        banner.save(update_fields=["display_order"])


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0013_remove_placeholder_hero_slides"),
    ]

    operations = [
        migrations.RunPython(place_after_categories, migrations.RunPython.noop),
    ]
