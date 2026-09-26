"""Admin controls and the customer journey around login, COD checkout and order tracking."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Address
from accounts.services import ensure_customer_profile_for_user
from cart.models import Cart, CartItem
from catalog.models import Category, Product
from core.models import Currency
from core.services import get_site_settings
from orders.models import Order
from payments.models import PaymentGatewayConfig
from shipping.models import Shipment


class AdminControlTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username="root", email="root@x.com", password="x")
        self.client.force_login(self.admin)

    def test_admin_pages_for_toggles_and_gateways_render(self):
        for path in (
            "/admin/core/featureflag/",
            "/admin/payments/paymentgatewayconfig/",
            "/admin/core/sitesettings/1/change/",
            "/dashboard/settings/",
        ):
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertIn("BROZIDO Admin", self.client.get("/admin/").content.decode())

    def test_gateway_list_shows_status_and_no_secret(self):
        site = get_site_settings()
        site.razorpay_key_id, site.razorpay_key_secret = "rzp_test_visible", "super-secret-value"
        site.save()
        html = self.client.get("/admin/payments/paymentgatewayconfig/").content.decode()
        self.assertIn("Live", html)
        self.assertNotIn("super-secret-value", html)

    def test_dashboard_settings_never_echo_secrets_in_clear_text(self):
        site = get_site_settings()
        site.razorpay_key_id, site.razorpay_key_secret = "rzp_test_visible", "super-secret-value"
        site.save()
        html = self.client.get("/dashboard/settings/").content.decode()
        self.assertIn('type="password"', html)

    def test_admin_can_enable_a_feature_through_the_changelist(self):
        flag = self.client.get("/admin/core/featureflag/")
        self.assertEqual(flag.status_code, 200)
        self.assertIn("Wishlist", flag.content.decode())


class CustomerJourneyTests(TestCase):
    def setUp(self):
        self.currency = Currency.objects.filter(is_default=True).first() or Currency.objects.first()
        category = Category.objects.create(name="Tees", slug="tees")
        self.product = Product.objects.create(
            name="Black Tee", slug="black-tee", category=category, base_price=Decimal("499"), hsn_code="6109", stock_quantity=10
        )
        self.user = get_user_model().objects.create_user(username="cust", email="cust@example.com", password="x")
        self.profile = ensure_customer_profile_for_user(user=self.user)

    def test_catalog_search_filter_and_sort_work_without_login(self):
        self.assertContains(self.client.get("/shop/"), "Black Tee")
        self.assertContains(self.client.get("/shop/?q=Black"), "Black Tee")
        self.assertContains(self.client.get("/shop/?in_stock=1&min_price=100&max_price=900&sort=price_asc"), "Black Tee")
        self.assertNotContains(self.client.get("/shop/?min_price=1000"), "Black Tee")
        self.assertContains(self.client.get("/shop/products/black-tee/"), "Add to Cart")

    def test_brand_filter_and_rating_sort_are_off(self):
        html = self.client.get("/shop/").content.decode()
        self.assertNotIn('name="brand"', html)
        self.assertNotIn("Top Rated", html)

    def test_checkout_requires_login_and_returns_to_checkout(self):
        response = self.client.get("/checkout/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/email-otp/", response["Location"])
        self.assertIn("next=/checkout/", response["Location"])
        self.assertEqual(self.client.post("/checkout/place-order/", {"gateway_key": "cod"}).status_code, 302)

    def test_guest_only_urls_and_password_login_are_hidden(self):
        for path in ("/accounts/guest-checkout/", "/accounts/password/forgot/", "/accounts/login/google/", "/accounts/login/otp/request/"):
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_email_otp_login_page_is_available(self):
        self.assertEqual(self.client.get("/accounts/login/email-otp/").status_code, 200)

    def _order(self, **kwargs) -> Order:
        return Order.objects.create(
            order_number="BRZ-2627-00042",
            customer_profile=self.profile,
            total_amount=Decimal("499"),
            currency=self.currency,
            delivery_address_snapshot={"email": "cust@example.com", "pincode": "682024"},
            **kwargs,
        )

    def test_track_order_by_number_needs_matching_email(self):
        self._order()
        self.assertEqual(self.client.get("/orders/track/").status_code, 200)
        wrong = self.client.post("/orders/track/", {"order_number": "BRZ-2627-00042", "email": "other@example.com"})
        self.assertContains(wrong, "find an order with that number")
        right = self.client.post("/orders/track/", {"order_number": "brz-2627-00042", "email": "CUST@example.com"})
        self.assertContains(right, "BRZ-2627-00042")
        self.assertNotContains(right, "find an order with that number")

    def test_tracking_shows_courier_awb_and_link_once_shipped(self):
        order = self._order()
        Shipment.objects.create(order=order, awb_code="AWB123", courier_name="Delhivery", current_status="in_transit")
        self.client.force_login(self.user)
        html = self.client.get(f"/orders/{order.pk}/tracking/").content.decode()
        self.assertIn("AWB123", html)
        self.assertIn("https://shiprocket.co/tracking/AWB123", html)

    def test_customer_cannot_track_someone_elses_order(self):
        order = self._order()
        other = get_user_model().objects.create_user(username="other", email="o@example.com", password="x")
        ensure_customer_profile_for_user(user=other)
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/orders/{order.pk}/tracking/").status_code, 404)


class CodCheckoutServerRulesTests(TestCase):
    """COD and gateway availability are enforced on place-order, not just hidden in the page."""

    def setUp(self):
        category = Category.objects.create(name="Tees", slug="tees")
        self.product = Product.objects.create(
            name="Black Tee", slug="black-tee", category=category, base_price=Decimal("499"), hsn_code="6109", stock_quantity=10
        )
        self.user = get_user_model().objects.create_user(username="cust", email="cust@example.com", password="x")
        self.profile = ensure_customer_profile_for_user(user=self.user)
        self.address = Address.objects.create(
            customer_profile=self.profile, label="Home",
            line1="1 Main Rd", pincode="682024", state_name="Kerala", city_name="Kochi",
        )
        self.client.force_login(self.user)
        cart = Cart.objects.create(customer_profile=self.profile, currency=self.profile.preferred_currency)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1, unit_price_at_add=Decimal("499"))

    def _place(self, gateway_key: str):
        return self.client.post(
            "/checkout/place-order/",
            {"gateway_key": gateway_key, "address_id": self.address.pk, "idempotency_key": f"k-{gateway_key}"},
            HTTP_HX_REQUEST="true",
        )

    def test_unavailable_gateway_is_rejected_before_an_order_exists(self):
        response = self._place("payu")  # PayU is OFF by default
        self.assertContains(response, "not available")
        self.assertFalse(Order.objects.exists())

    def test_cod_blocked_for_the_delivery_state_is_rejected(self):
        site = get_site_settings()
        site.cod_disabled_states = "Kerala"
        site.save()
        response = self._place("cod")
        self.assertContains(response, "not available")
        self.assertFalse(Order.objects.exists())

    def test_cod_globally_off_is_rejected(self):
        site = get_site_settings()
        site.cod_enabled = False
        site.save()
        self.assertContains(self._place("cod"), "not available")
        self.assertFalse(Order.objects.exists())

    def test_gateway_seed_is_razorpay_primary(self):
        self.assertTrue(PaymentGatewayConfig.objects.get(gateway="razorpay").is_primary)

    def test_cod_order_is_placed_confirmed_and_left_payable_on_delivery(self):
        response = self._place("cod")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/checkout/confirmation/", response["HX-Redirect"])
        order = Order.objects.get()
        self.assertTrue(order.is_cod)
        self.assertEqual(order.payment_transactions.get().status, "pending")
        self.assertEqual(Product.objects.get(pk=self.product.pk).stock_quantity, 9)
