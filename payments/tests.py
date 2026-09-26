"""Gateway configuration (Razorpay / PayU) and cash on delivery."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product
from core.models import Currency
from core.services import get_site_settings
from orders.models import Order, OrderItem
from payments.gateways import cod_available_for, get_available_gateways
from payments.models import PaymentGatewayConfig, PaymentStatus
from payments.services import process_payment, transition_payment_status


def configure(**fields) -> None:
    site = get_site_settings()
    for name, value in fields.items():
        setattr(site, name, value)
    site.save()


RAZORPAY = {"razorpay_key_id": "rzp_test_1", "razorpay_key_secret": "secret"}
PAYU = {"payu_merchant_key": "payu-key", "payu_merchant_salt": "payu-salt"}


class GatewayConfigTests(TestCase):
    def setUp(self):
        configure(**RAZORPAY)

    def test_defaults_are_razorpay_primary_and_payu_off(self):
        razorpay = PaymentGatewayConfig.objects.get(gateway="razorpay")
        payu = PaymentGatewayConfig.objects.get(gateway="payu")
        self.assertTrue(razorpay.is_enabled and razorpay.is_primary)
        self.assertFalse(payu.is_enabled or payu.is_primary)

    def test_only_razorpay_methods_offered_by_default(self):
        keys = set(get_available_gateways())
        self.assertEqual(keys, {"razorpay_upi", "razorpay_card", "razorpay_netbanking", "razorpay_wallet"})

    def test_razorpay_without_credentials_is_not_offered(self):
        configure(razorpay_key_id="", razorpay_key_secret="")
        self.assertEqual(get_available_gateways(), {})

    def test_payu_cannot_be_enabled_without_its_own_credentials(self):
        payu = PaymentGatewayConfig.objects.get(gateway="payu")
        payu.is_enabled = True
        with self.assertRaises(ValidationError):
            payu.full_clean()  # Razorpay credentials do not count for PayU

    def test_payu_enabled_alongside_razorpay_keeps_providers_separate(self):
        configure(**PAYU)
        payu = PaymentGatewayConfig.objects.get(gateway="payu")
        payu.is_enabled = True
        payu.full_clean()
        payu.save()
        keys = set(get_available_gateways())
        self.assertIn("payu", keys)
        self.assertIn("razorpay_upi", keys)

    def test_payu_only_hides_razorpay(self):
        configure(**PAYU)
        PaymentGatewayConfig.objects.filter(gateway="razorpay").update(is_enabled=False, is_primary=False)
        PaymentGatewayConfig.objects.filter(gateway="payu").update(is_enabled=True, is_primary=True)
        self.assertEqual(set(get_available_gateways()), {"payu"})

    def test_saving_a_new_primary_demotes_the_previous_one(self):
        configure(**PAYU)
        payu = PaymentGatewayConfig.objects.get(gateway="payu")
        payu.is_enabled = payu.is_primary = True
        payu.save()
        self.assertFalse(PaymentGatewayConfig.objects.get(gateway="razorpay").is_primary)
        self.assertEqual(PaymentGatewayConfig.objects.filter(is_primary=True).count(), 1)

    def test_primary_must_be_enabled(self):
        payu = PaymentGatewayConfig.objects.get(gateway="payu")
        payu.is_primary = True
        with self.assertRaises(ValidationError):
            payu.full_clean()


class CodAvailabilityTests(TestCase):
    def test_on_by_default_everywhere(self):
        self.assertTrue(cod_available_for(state="Kerala", pincode="682024"))

    def test_global_switch(self):
        configure(cod_enabled=False)
        self.assertFalse(cod_available_for(state="Kerala", pincode="682024"))

    def test_blocked_state_pincode_and_prefix(self):
        configure(cod_disabled_states="Assam\nKerala ", cod_disabled_pincodes="560001\n7000*")
        self.assertFalse(cod_available_for(state="kerala", pincode="682024"))
        self.assertFalse(cod_available_for(state="Karnataka", pincode="560001"))
        self.assertFalse(cod_available_for(state="West Bengal", pincode="700091"))
        self.assertTrue(cod_available_for(state="Karnataka", pincode="560002"))


class CodOrderTests(TestCase):
    def setUp(self):
        currency = Currency.objects.filter(is_default=True).first() or Currency.objects.first()
        category = Category.objects.create(name="Cat", slug="cat")
        self.product = Product.objects.create(
            name="Tee", slug="tee", category=category, base_price=Decimal("100"), hsn_code="6109", stock_quantity=5
        )
        self.order = Order.objects.create(order_number="BRZ-2627-00001", total_amount=Decimal("100"), currency=currency)
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2, unit_price=Decimal("50")
        )

    def stock(self) -> int:
        return Product.objects.get(pk=self.product.pk).stock_quantity

    def test_cod_confirms_the_order_but_leaves_payment_pending(self):
        tx = process_payment(order=self.order, gateway_key="cod", payment_data={})
        self.assertEqual(tx.status, PaymentStatus.PENDING)
        self.assertEqual(self.stock(), 3)
        self.assertTrue(self.order.is_cod)
        self.assertEqual(self.order.payment_method_display, "Cash on Delivery")

    def test_marking_cod_paid_later_does_not_take_stock_twice(self):
        tx = process_payment(order=self.order, gateway_key="cod", payment_data={})
        transition_payment_status(payment_transaction=tx, new_status=PaymentStatus.SUCCESS)
        tx.refresh_from_db()
        self.assertEqual(tx.status, PaymentStatus.SUCCESS)
        self.assertEqual(self.stock(), 3)
