"""
Central feature-flag registry for optional storefront modules.

Every optional module is declared once in ``FEATURES``. Admins flip flags in
Django Admin (Core -> Feature flags); code asks ``is_enabled(key)``, templates
use ``{% if features.<key> %}`` and URLs are guarded with ``feature_required``.
A flag that is OFF hides the module everywhere — its models, migrations,
services and admin stay in place so turning it back ON restores it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse
from django.urls import path

CACHE_KEY = "core:feature-flags:v1"


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    description: str
    default: bool = False


FEATURES: tuple[Feature, ...] = (
    Feature("coupons", "Coupons", "Coupon codes at cart and checkout."),
    Feature("flash_sales", "Flash sales", "Time-limited discounted prices."),
    Feature("referrals", "Referrals", "Customer referral programme."),
    Feature("newsletter", "Newsletter", "Newsletter sign-up form and homepage block."),
    Feature("abandoned_cart", "Abandoned cart recovery", "Reminders for abandoned carts."),
    Feature("brands", "Brands", "Brand pages, filters and the homepage brand strip."),
    Feature("reviews", "Reviews", "Customer product reviews and the homepage reviews block."),
    Feature("combos", "Combos", "Combo bundles and the homepage combos block."),
    Feature("wishlist", "Wishlist", "Wishlist hearts, page and shared wishlists."),
    Feature("product_videos", "Product videos", "Video on product pages."),
    Feature("related_products", "Related products", "Related / similar products on product pages."),
    Feature("product_documents", "Product documents", "Downloadable documents on product pages."),
    Feature("subscriptions", "Subscriptions", "Recurring subscription orders."),
    Feature("rentals", "Rentals", "Rental products."),
    Feature("corporate_accounts", "Corporate accounts", "B2B corporate registration."),
    Feature("blog", "Blog", "Blog listing."),
    Feature("saved_payment_methods", "Saved payment methods", "Stored payment methods in the account."),
    Feature("google_login", "Google login", "Sign in with Google."),
    Feature("phone_login", "Phone OTP login", "Login by phone-number OTP."),
    Feature("password_login", "Password login", "Password login and password reset (email OTP is the standard login)."),
    Feature("guest_checkout", "Guest checkout", "Checkout without logging in."),
    Feature("multi_currency", "Currency / country switcher", "Currency and country selectors."),
    Feature("occasion_shopping", "Shop by occasion / recipient", "Occasion and recipient homepage blocks."),
    Feature("instagram_gallery", "Instagram gallery", "Instagram homepage block."),
    Feature("marketing_cards", "Marketing feature cards", "Promotional feature cards on the homepage."),
)

FEATURES_BY_KEY: dict[str, Feature] = {f.key: f for f in FEATURES}
FEATURE_CHOICES = [(f.key, f.label) for f in FEATURES]


def _load() -> dict[str, bool]:
    states = cache.get(CACHE_KEY)
    if states is None:
        from core.models import FeatureFlag

        stored = dict(FeatureFlag.objects.values_list("key", "is_enabled"))
        states = {f.key: stored.get(f.key, f.default) for f in FEATURES}
        cache.set(CACHE_KEY, states, getattr(settings, "FEATURE_FLAGS_CACHE_SECONDS", 60))
    return states


def clear_cache() -> None:
    cache.delete(CACHE_KEY)


def is_enabled(key: str) -> bool:
    """Return whether a feature is ON. Unknown keys are a programming error."""
    if key not in FEATURES_BY_KEY:
        raise KeyError(f"Unknown feature: {key}")
    return _load()[key]


class FeatureStates:
    """Template helper: ``{% if features.coupons %}``."""

    def __getattr__(self, key: str) -> bool:
        if key.startswith("_") or key not in FEATURES_BY_KEY:
            raise AttributeError(key)
        return is_enabled(key)


def feature_required(key: str) -> Callable:
    """View decorator: respond 404 while the feature is OFF."""

    def decorator(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view)
        def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not is_enabled(key):
                raise Http404("This feature is not available.")
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def feature_path(feature: str, route: str, view: Callable, **kwargs):
    """``path()`` whose view answers 404 while ``feature`` is OFF."""
    return path(route, feature_required(feature)(view), **kwargs)
