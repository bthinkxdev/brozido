"""URL routing for the catalog app."""

from __future__ import annotations

from django.urls import path

from core.features import feature_path

from catalog import views

app_name = "catalog"

urlpatterns = [
    path("search/suggest/", views.search_suggestions_view, name="search-suggest"),
    feature_path("rentals", "rentals/", views.rental_list_view, name="rental-list"),
    feature_path("combos", "combos/", views.combo_list_view, name="combo-list"),
    feature_path("combos", "combos/<slug:slug>/", views.combo_detail_view, name="combo-detail"),
    path("products/<slug:slug>/", views.pdp_view, name="pdp"),
    feature_path("reviews", "products/<int:product_id>/review/", views.submit_review_view, name="submit-review"),
    path(
        "products/<int:product_id>/variant-price/",
        views.variant_price_view,
        name="variant-price",
    ),
    path(
        "products/<int:product_id>/delivery-estimate/",
        views.delivery_estimate_view,
        name="delivery-estimate",
    ),
    path("category/<slug:category_slug>/", views.plp_view, name="plp-category"),
    path("", views.plp_view, name="plp"),
]
