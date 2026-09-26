"""Django admin registrations for the core app."""

from __future__ import annotations

from django.contrib import admin

from core.forms import CurrencyAdminForm
from core import features
from core.models import Currency, FeatureFlag, SiteSettings


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    """Admin interface for storefront currencies."""

    form = CurrencyAdminForm
    list_display = ("code", "symbol", "exchange_rate_to_base", "is_default", "updated_at")
    list_filter = ("is_default",)
    search_fields = ("code", "symbol")
    ordering = ("code",)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton site settings — only one row (pk=1)."""

    def has_add_permission(self, request) -> bool:
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    """Turn optional storefront modules ON or OFF. Rows are created automatically."""

    list_display = ("label", "is_enabled", "description")
    list_editable = ("is_enabled",)
    list_display_links = ("label",)
    readonly_fields = ("key",)
    ordering = ("key",)

    @admin.display(description="Feature", ordering="key")
    def label(self, obj: FeatureFlag) -> str:
        return str(obj)

    @admin.display(description="What it controls")
    def description(self, obj: FeatureFlag) -> str:
        feature = features.FEATURES_BY_KEY.get(obj.key)
        return feature.description if feature else ""

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
