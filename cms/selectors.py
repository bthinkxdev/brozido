"""Read-only query functions for the cms app; views must not call the ORM directly."""

from __future__ import annotations

from typing import Any

from django.core.cache import cache

from core.features import is_enabled

HOMEPAGE_SECTIONS_CACHE_KEY = "cms:homepage_sections:active:v1"
HOMEPAGE_SECTIONS_CACHE_TTL = 300

# Homepage blocks that belong to an optional feature; hidden while it is OFF.
SECTION_FEATURES = {
    "featured_brands": "brands",
    "reviews": "reviews",
    "combos": "combos",
    "instagram_gallery": "instagram_gallery",
    "newsletter": "newsletter",
    "subscription_banner": "subscriptions",
    "marketing_features": "marketing_cards",
    "shop_by_occasion": "occasion_shopping",
    "shop_by_recipient": "occasion_shopping",
    "corporate_gifts_banner": "corporate_accounts",
}


def get_active_homepage_sections() -> list[dict[str, Any]]:
    """
    Return ordered active homepage sections from the Redis-cached snapshot.

    Query guarantee: 0 DB queries on cache hit. On cache miss the Celery task
    `cms.tasks.refresh_homepage_cache` repopulates the snapshot (1 SELECT).

    Cache key: cms:homepage_sections:active:v1
    TTL: 300 seconds (HOMEPAGE_SECTIONS_CACHE_TTL)

    Returns:
        List of section dicts with keys: id, section_type, title, display_order, config.
    """
    snapshot = cache.get(HOMEPAGE_SECTIONS_CACHE_KEY)
    if snapshot is None:
        from cms.services import build_homepage_sections_snapshot

        snapshot = build_homepage_sections_snapshot()
        try:
            cache.set(HOMEPAGE_SECTIONS_CACHE_KEY, snapshot, timeout=HOMEPAGE_SECTIONS_CACHE_TTL)
        except Exception:
            pass
    return [
        section
        for section in snapshot
        if SECTION_FEATURES.get(section["section_type"]) is None
        or is_enabled(SECTION_FEATURES[section["section_type"]])
    ]


def get_hero_slides() -> list[dict[str, Any]]:
    """
    Return active hero slides (uploaded photos/videos) ordered for display.

    Query guarantee: exactly 1 SELECT on cms_heroslide.

    Returns:
        List of slide dicts with keys: type, src, poster, title.
        Slides without any media file are skipped.
    """
    from cms.models import HeroSlide

    slides: list[dict[str, Any]] = []
    for slide in HeroSlide.objects.filter(is_active=True).order_by("display_order", "id"):
        src = slide.media_src
        if not src:
            continue
        slides.append(
            {
                "type": slide.media_type,
                "src": src,
                "poster": slide.poster_src,
                "title": slide.title,
            }
        )
    return slides


def get_secondary_slides() -> list[dict[str, Any]]:
    """
    Return active secondary banner slides (9:3 ratio) ordered for display.

    Query guarantee: exactly 1 SELECT on cms_secondaryslide.

    Returns:
        List of slide dicts with keys: type, src, poster, title.
        Slides without any media file are skipped.
    """
    from cms.models import SecondarySlide

    slides: list[dict[str, Any]] = []
    for slide in SecondarySlide.objects.filter(is_active=True).order_by("display_order", "id"):
        src = slide.media_src
        if not src:
            continue
        slides.append(
            {
                "type": slide.media_type,
                "src": src,
                "poster": slide.poster_src,
                "title": slide.title,
            }
        )
    return slides
