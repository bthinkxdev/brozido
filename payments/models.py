"""Data layer for the payments app — models only, no business logic."""

from __future__ import annotations

from django.db import models, transaction

from core.models import TimeStampedModel


class PaymentStatus(models.TextChoices):
    """Payment transaction lifecycle."""

    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class PaymentTransaction(TimeStampedModel):
    """Record of a payment attempt for an order."""

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payment_transactions",
        verbose_name="Order",
    )
    gateway_key = models.CharField(max_length=40, db_index=True, verbose_name="Gateway key")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount")
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="payment_transactions",
        verbose_name="Currency",
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
        verbose_name="Status",
    )
    external_intent_id = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
        verbose_name="External intent ID",
    )
    external_transaction_id = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="External transaction ID",
    )
    attempted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Attempted at",
        help_text="When the customer actually engaged the gateway's checkout "
        "widget (e.g. clicked Pay Now), as opposed to just having a pending "
        "intent created server-side at order placement. Null means the customer "
        "never made it this far — used to keep such orders out of the "
        "Abandoned Checkout list until there was something to actually abandon.",
    )
    metadata = models.JSONField(default=dict, verbose_name="Metadata")

    class Meta:
        verbose_name = "Payment transaction"
        verbose_name_plural = "Payment transactions"
        indexes = [
            models.Index(fields=["order", "status"], name="pay_tx_order_status_idx"),
            models.Index(fields=["gateway_key", "status"], name="pay_tx_gateway_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.gateway_key} {self.amount} ({self.status})"


class RazorpayWebhookEventStatus(models.TextChoices):
    """
    Terminal outcome of the first time an event_id was processed.

    Deliberately has no "duplicate" member: a redelivery is a runtime fact
    (get_or_create's ``created`` flag), not something that should overwrite the
    original outcome recorded here.
    """

    PROCESSED = "processed", "Processed"
    UNKNOWN_TRANSACTION = "unknown_transaction", "Unknown transaction"
    AMOUNT_MISMATCH = "amount_mismatch", "Amount mismatch"
    CURRENCY_MISMATCH = "currency_mismatch", "Currency mismatch"
    PAYMENT_ID_MISMATCH = "payment_id_mismatch", "Payment ID mismatch"
    IGNORED_EVENT_TYPE = "ignored_event_type", "Ignored event type"
    ERROR = "error", "Error"


class RazorpayWebhookEvent(TimeStampedModel):
    """
    Durable, DB-backed dedup + audit record for one Razorpay webhook delivery.

    ``event_id`` (from the ``X-Razorpay-Event-Id`` header) is unique per event —
    this is the permanent idempotency gate for webhook retries, independent of
    the PaymentTransaction-level status guard in payments.services which handles
    the separate case of two *different* event_ids (e.g. payment.captured and
    order.paid) referring to the same payment.
    """

    event_id = models.CharField(max_length=80, unique=True, db_index=True, verbose_name="Razorpay event ID")
    event_type = models.CharField(max_length=60, db_index=True, verbose_name="Event type")
    razorpay_order_id = models.CharField(max_length=120, blank=True, db_index=True, verbose_name="Razorpay order ID")
    razorpay_payment_id = models.CharField(max_length=120, blank=True, verbose_name="Razorpay payment ID")
    payload = models.JSONField(default=dict, verbose_name="Payload")
    payment_transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="razorpay_webhook_events",
        verbose_name="Payment transaction",
    )
    status = models.CharField(
        max_length=24,
        choices=RazorpayWebhookEventStatus.choices,
        db_index=True,
        verbose_name="Status",
    )

    class Meta:
        verbose_name = "Razorpay webhook event"
        verbose_name_plural = "Razorpay webhook events"

    def __str__(self) -> str:
        return f"{self.event_type} {self.event_id} ({self.status})"


class PaymentGatewayConfig(TimeStampedModel):
    """
    Admin-controlled availability of one payment provider ("family").

    Each provider (Razorpay, PayU) is an independent integration with its own
    credentials on SiteSettings and its own adapters; this row only says whether
    checkout may offer it and which one is primary. See payments.gateways.
    """

    class Gateway(models.TextChoices):
        RAZORPAY = "razorpay", "Razorpay"
        PAYU = "payu", "PayU"

    gateway = models.CharField(max_length=20, choices=Gateway.choices, unique=True)
    is_enabled = models.BooleanField(
        default=False,
        help_text="Offer this gateway at checkout. Requires its credentials to be configured.",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="The default gateway, listed first at checkout. Exactly one enabled gateway is primary.",
    )

    class Meta:
        verbose_name = "Payment gateway"
        verbose_name_plural = "Payment gateways"

    def __str__(self) -> str:
        return self.get_gateway_display()

    def save(self, *args, **kwargs) -> None:
        with transaction.atomic():
            if self.is_primary:
                PaymentGatewayConfig.objects.exclude(pk=self.pk).filter(is_primary=True).update(is_primary=False)
            super().save(*args, **kwargs)

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        from payments.gateways import credentials_configured

        if self.is_primary and not self.is_enabled:
            raise ValidationError({"is_primary": "A gateway must be enabled to be the primary gateway."})
        if self.is_enabled and not credentials_configured(self.gateway):
            raise ValidationError(
                {"is_enabled": f"Add the {self.get_gateway_display()} credentials in Site settings before enabling it."}
            )
