"""Cross-app signal handlers for the core app (side effects only)."""

from __future__ import annotations

from django.db.models.signals import post_delete, post_migrate, post_save
from django.dispatch import receiver

from core import features
from core.models import FeatureFlag


@receiver([post_save, post_delete], sender=FeatureFlag)
def clear_feature_cache(sender, **kwargs) -> None:
    features.clear_cache()


@receiver(post_migrate)
def ensure_feature_flag_rows(sender, **kwargs) -> None:
    """Create a row (at its registry default) for every declared feature so admins can see it."""
    if sender.name != "core":
        return
    using = kwargs.get("using", "default")
    existing = set(FeatureFlag.objects.using(using).values_list("key", flat=True))
    FeatureFlag.objects.using(using).bulk_create(
        [FeatureFlag(key=f.key, is_enabled=f.default) for f in features.FEATURES if f.key not in existing]
    )
    features.clear_cache()
