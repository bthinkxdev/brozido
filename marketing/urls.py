"""URL routing for the marketing app."""

from __future__ import annotations

from django.urls import path

from core.features import feature_path

from marketing import views

app_name = "marketing"

urlpatterns = [
    feature_path("newsletter", "newsletter/subscribe/", views.newsletter_subscribe_view, name="newsletter-subscribe"),
]