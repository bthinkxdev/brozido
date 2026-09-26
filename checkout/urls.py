"""URL routing for the checkout app."""

from __future__ import annotations

from django.urls import path

from core.features import feature_path

from checkout import views

app_name = "checkout"

urlpatterns = [
    path("", views.checkout_view, name="checkout"),
    path("place-order/", views.checkout_place_order_view, name="place-order"),
    path("address/<int:address_id>/update/", views.checkout_address_update_view, name="address-update"),
    feature_path("coupons", "coupon/apply/", views.checkout_coupon_apply_view, name="coupon-apply"),
    feature_path("coupons", "coupon/remove/", views.checkout_coupon_remove_view, name="coupon-remove"),
    path("confirmation/<int:order_id>/", views.checkout_confirmation_view, name="confirmation"),
    path("pay/razorpay/<int:order_id>/", views.razorpay_pay_view, name="razorpay-pay"),
    path("pay/razorpay/<int:order_id>/attempt/", views.razorpay_attempt_view, name="razorpay-attempt"),
    path("pay/razorpay/callback/", views.razorpay_callback_view, name="razorpay-callback"),
    path("pay/payu/<int:order_id>/", views.payu_pay_view, name="payu-pay"),
    path("pay/payu/<int:order_id>/attempt/", views.payu_attempt_view, name="payu-attempt"),
    path("pay/payu/callback/", views.payu_callback_view, name="payu-callback"),
]
