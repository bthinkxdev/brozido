"""
Delete media files that no database row references any more.

Walks every model's FileField/ImageField (via Django's own app registry, so it
never goes stale as fields are added or removed) to build the set of file paths
actually in use, then compares that against everything physically present under
MEDIA_ROOT. Anything on disk but not referenced anywhere is orphaned — usually
left behind by a deleted row, an old import, or a field that no longer exists.

Defaults to a dry run. Pass --apply to actually delete.

Usage:
    python manage.py prune_unused_media            # list what would be removed
    python manage.py prune_unused_media --apply     # actually remove it
"""

from __future__ import annotations

import os

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models


class Command(BaseCommand):
    help = "Delete media files under MEDIA_ROOT that no database row references (dry run unless --apply)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--apply", action="store_true", help="Actually delete the orphaned files (default: dry run)."
        )

    def handle(self, *args, **options) -> None:
        media_root = str(settings.MEDIA_ROOT)

        referenced: set[str] = set()
        for model in apps.get_models():
            file_fields = [
                f for f in model._meta.get_fields()
                if isinstance(f, (models.FileField, models.ImageField))
            ]
            if not file_fields:
                continue
            values = model._default_manager.values_list(*(f.name for f in file_fields))
            for row in values:
                for value in row:
                    if value:
                        referenced.add(os.path.normpath(str(value)))

        on_disk: list[str] = []
        for root, _dirs, files in os.walk(media_root):
            for filename in files:
                full_path = os.path.join(root, filename)
                rel_path = os.path.normpath(os.path.relpath(full_path, media_root))
                on_disk.append(rel_path)

        orphaned = sorted(p for p in on_disk if p not in referenced)

        if not orphaned:
            self.stdout.write(self.style.SUCCESS("No orphaned media files found."))
            return

        total_bytes = sum(os.path.getsize(os.path.join(media_root, p)) for p in orphaned)
        self.stdout.write(f"{len(orphaned)} orphaned file(s), {total_bytes / (1024 * 1024):.1f} MB:")
        for p in orphaned:
            self.stdout.write(f"  {p}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("\nDry run only — re-run with --apply to delete these."))
            return

        removed = 0
        for p in orphaned:
            try:
                os.remove(os.path.join(media_root, p))
                removed += 1
            except OSError as exc:
                self.stderr.write(f"Could not remove {p}: {exc}")

        # Clean up directories left empty by the deletions above (deepest first).
        # os.walk's per-directory listing is captured before this loop deletes
        # anything, so it goes stale as children disappear — rmdir succeeding
        # or raising is the only reliable "is it actually empty now" check.
        for root, _dirs, _files in os.walk(media_root, topdown=False):
            if root == media_root:
                continue
            try:
                os.rmdir(root)
            except OSError:
                pass

        self.stdout.write(self.style.SUCCESS(f"Removed {removed} orphaned file(s) ({total_bytes / (1024 * 1024):.1f} MB)."))
