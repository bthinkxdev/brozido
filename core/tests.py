"""Feature flags, brand configuration and policy pages."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from core import features
from core.models import FeatureFlag
from core.services import get_site_settings
from marketing.exceptions import InvalidCouponError
from marketing.services import validate_coupon_for_cart


def set_feature(key: str, enabled: bool) -> None:
    FeatureFlag.objects.update_or_create(key=key, defaults={"is_enabled": enabled})


class FeatureFlagTests(TestCase):
    def test_every_registered_feature_has_a_row_and_is_off_by_default(self):
        self.assertEqual(FeatureFlag.objects.count(), len(features.FEATURES))
        for feature in features.FEATURES:
            self.assertFalse(features.is_enabled(feature.key), feature.key)

    def test_unknown_feature_is_a_programming_error(self):
        with self.assertRaises(KeyError):
            features.is_enabled("does_not_exist")

    def test_toggle_takes_effect_immediately(self):
        set_feature("combos", True)
        self.assertTrue(features.is_enabled("combos"))
        set_feature("combos", False)
        self.assertFalse(features.is_enabled("combos"))

    def test_off_feature_url_is_404_and_on_restores_it(self):
        self.assertEqual(self.client.get("/shop/combos/").status_code, 404)
        self.assertEqual(self.client.get("/accounts/wishlist/").status_code, 404)
        set_feature("combos", True)
        self.assertEqual(self.client.get("/shop/combos/").status_code, 200)

    def test_coupons_cannot_be_applied_while_off(self):
        from decimal import Decimal

        with self.assertRaises(InvalidCouponError):
            validate_coupon_for_cart(code="ANY", cart_subtotal=Decimal("100"))

    def test_off_features_are_hidden_from_the_storefront_chrome(self):
        html = self.client.get("/").content.decode()
        self.assertNotIn("jm-header-wishlist", html)
        self.assertNotIn("/shop/combos/", html)
        set_feature("wishlist", True)
        self.assertIn("jm-header-wishlist", self.client.get("/").content.decode())


class BrandTests(TestCase):
    def test_storefront_shows_brozido_contact_details_and_no_previous_brand(self):
        for path in ("/", "/contact-us/", "/about-us/"):
            html = self.client.get(path).content.decode()
            self.assertNotIn("ZAYE", html.upper(), path)
            self.assertNotIn("FLOWARD", html.upper(), path)
            self.assertIn("BROZIDO", html, path)
        contact = self.client.get("/contact-us/").content.decode()
        for value in ("9744015184", "Ajaysreekrishnapuram123@gmail.com", "brozido@gmail.com"):
            self.assertIn(value, contact)
        self.assertIn("https://wa.me/919744015184", self.client.get("/").content.decode())

    def test_about_us_uses_client_copy(self):
        html = self.client.get("/about-us/").content.decode()
        self.assertIn("your trusted one-stop destination", html)
        self.assertIn("www.brozido.com", html)

    @override_settings(GOOGLE_ANALYTICS_ID="G-TEST123")
    def test_google_analytics_only_rendered_when_configured(self):
        self.assertIn("G-TEST123", self.client.get("/").content.decode())

    def test_google_analytics_absent_by_default(self):
        self.assertNotIn("googletagmanager", self.client.get("/").content.decode())


class PolicyPageTests(TestCase):
    def test_every_policy_page_renders_with_its_required_terms(self):
        expectations = {
            "/policies/shipping-and-delivery/": ["same day", "2–3 days"],
            "/policies/returns-and-refunds/": ["3 days", "Unwashed", "original packaging", "5–7 business days", "non-refundable"],
            "/policies/cancellation-and-refunds/": ["before it is dispatched", "banking timelines"],
            "/policies/terms-and-conditions/": ["Fraudulent", "Prices may change", "Intellectual property"],
            "/policies/payment-information/": ["UPI", "Cash on Delivery"],
            "/policies/security/": ["SSL/TLS", "encrypted"],
            "/privacy-policy/": ["Order processing", "Service delivery", "Legal compliance", "unauthorized third parties"],
        }
        for path, phrases in expectations.items():
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            html = response.content.decode()
            for phrase in phrases:
                self.assertIn(phrase, html, f"{path}: {phrase}")

    def test_unknown_policy_is_404(self):
        self.assertEqual(self.client.get("/policies/nope/").status_code, 404)


class SiteSettingsValidationTests(TestCase):
    def test_clearing_credentials_of_an_enabled_gateway_is_refused(self):
        site = get_site_settings()
        site.razorpay_key_id = ""
        site.razorpay_key_secret = ""
        with self.assertRaises(ValidationError) as ctx:
            site.clean()
        self.assertIn("razorpay_key_id", ctx.exception.message_dict)
