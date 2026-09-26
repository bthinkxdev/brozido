"""URL routing for the accounts app."""

from __future__ import annotations

from django.urls import path

from core.features import feature_path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.email_register_view, name="register"),
    path("login/email-otp/", views.email_otp_request_view, name="login-email-otp"),
    path("verify-email-otp/", views.email_otp_verify_view, name="verify-email-otp"),
    path("verify-email-otp/resend/", views.email_otp_resend_view, name="resend-email-otp"),
    path("logout/", views.email_logout_view, name="logout"),
    feature_path("phone_login", "login/otp/request/", views.otp_request_view, name="otp-request"),
    feature_path("phone_login", "login/otp/verify/", views.otp_verify_view, name="otp-verify"),
    feature_path("google_login", "login/google/", views.google_login_view, name="login-google"),
    feature_path("guest_checkout", "guest-checkout/", views.guest_checkout_view, name="guest-checkout"),
    feature_path("password_login", "password/forgot/", views.forgot_password_view, name="forgot-password"),
    feature_path("password_login", "password/reset/", views.reset_password_view, name="reset-password"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/edit/", views.edit_profile_view, name="edit-profile"),
    path("dashboard/orders/<int:pk>/invoice/", views.customer_invoice_detail, name="customer-invoice"),
    path("addresses/", views.address_list_create_view, name="address-list-create"),
    path("addresses/<int:address_id>/", views.address_detail_view, name="address-detail"),
    feature_path("saved_payment_methods", "payment-methods/", views.payment_methods_list_view, name="payment-methods-list"),
    feature_path("saved_payment_methods", 
        "payment-methods/<int:payment_method_id>/delete/",
        views.payment_method_delete_view,
        name="payment-method-delete",
    ),

    feature_path("wishlist", "wishlist/shared/", views.wishlist_shared_view, name="wishlist-shared"),
    feature_path("wishlist", "wishlist/add/", views.wishlist_add_view, name="wishlist-add"),
    feature_path("wishlist", "wishlist/remove/", views.wishlist_remove_view, name="wishlist-remove"),
    feature_path("wishlist", 
        "wishlist/shared/mutate/",
        views.wishlist_shared_mutate_view,
        name="wishlist-shared-mutate",
    ),
    feature_path("wishlist", "wishlist/", views.wishlist_view, name="wishlist"),

    feature_path("subscriptions", "subscriptions/", views.subscription_list_view, name="subscription-list"),
    feature_path("subscriptions", "subscriptions/create/", views.subscription_create_view, name="subscription-create"),
    feature_path("subscriptions", 
        "subscriptions/<int:subscription_id>/pause/",
        views.subscription_pause_view,
        name="subscription-pause",
    ),
    feature_path("subscriptions", 
        "subscriptions/<int:subscription_id>/resume/",
        views.subscription_resume_view,
        name="subscription-resume",
    ),
    feature_path("subscriptions", 
        "subscriptions/<int:subscription_id>/cancel/",
        views.subscription_cancel_view,
        name="subscription-cancel",
    ),
]
