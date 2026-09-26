"""Move existing SiteSettings from the previous brand to BROZIDO (only rows still on old values)."""

from django.db import migrations

LEGACY_NAMES = ("zaye", "lennox", "desert", "floward")
LEGACY_EMAILS = ("zayelennox@gmail.com", "desertmobiles@gmail.com")
LEGACY_WHATSAPP = ("919292773339", "971503131065", "8891386206")


def to_brozido(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    row = SiteSettings.objects.filter(pk=1).first()
    if row is None:
        return
    if any(token in (row.site_name or "").lower() for token in LEGACY_NAMES):
        row.site_name = "BROZIDO"
        row.logo = None
    if (row.vendor_email or "").lower() in LEGACY_EMAILS:
        row.vendor_email = "brozido@gmail.com"
    if (row.whatsapp_number or "").replace("+", "") in LEGACY_WHATSAPP:
        row.whatsapp_number = "919744015184"
    row.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_featureflag"),
    ]

    operations = [
        migrations.RunPython(to_brozido, migrations.RunPython.noop),
    ]
