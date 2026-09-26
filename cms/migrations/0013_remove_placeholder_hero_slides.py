"""Drop the seeded placehold.co / Floward demo slides from homepage section config."""

from django.db import migrations

PLACEHOLDER_MARKERS = ("placehold.co", "floward")


def remove_placeholder_slides(apps, schema_editor):
    HomepageSection = apps.get_model("cms", "HomepageSection")
    for section in HomepageSection.objects.filter(section_type__in=["hero_slider", "secondary_banner"]):
        slides = (section.config or {}).get("slides") or []
        kept = [
            slide
            for slide in slides
            if not any(marker in str(slide).lower() for marker in PLACEHOLDER_MARKERS)
        ]
        if len(kept) != len(slides):
            section.config = {**section.config, "slides": kept}
            section.save(update_fields=["config"])


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0012_alter_homepagesection_section_type"),
    ]

    operations = [
        migrations.RunPython(remove_placeholder_slides, migrations.RunPython.noop),
    ]
