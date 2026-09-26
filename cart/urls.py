"""URL routing for the cart app."""

from __future__ import annotations

from django.urls import path

from core.features import feature_path

from cart import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_page_view, name="page"),
    path("drawer/", views.cart_drawer_view, name="drawer"),
    path("count/", views.cart_count_view, name="count"),
    path("add/", views.cart_add_view, name="add"),
    feature_path("combos", "combo/add/", views.cart_add_combo_view, name="combo-add"),
    feature_path("combos", "combo/remove/", views.cart_remove_combo_view, name="combo-remove"),
    feature_path("combos", "combo/quantity/", views.cart_combo_quantity_view, name="combo-quantity"),
    path("remove/", views.cart_remove_view, name="remove"),
    path("page/remove/", views.cart_page_remove_view, name="page-remove"),
    path("quantity/", views.cart_quantity_view, name="quantity"),
    feature_path("coupons", "coupon/apply/", views.cart_coupon_apply_view, name="coupon-apply"),
    feature_path("coupons", "coupon/remove/", views.cart_coupon_remove_view, name="coupon-remove"),
    feature_path("wishlist", "wishlist/toggle/", views.wishlist_toggle_view, name="wishlist-toggle"),
    feature_path("wishlist", "wishlist/count/", views.wishlist_count_view, name="wishlist-count"),
]
