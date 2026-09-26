"""
Central payment-gateway configuration: which providers checkout may offer.

Razorpay and PayU are separate integrations (own adapters, credentials, callbacks,
webhooks). Checkout never branches on a provider name; it asks this module which
registered adapters are currently available and which one is primary.
"""

from __future__ import annotations

from payments.adapters.concrete import _get_payu_credentials, _get_razorpay_credentials
from payments.models import PaymentGatewayConfig
from payments.registry import PAYMENT_GATEWAYS

_CREDENTIAL_LOADERS = {
    PaymentGatewayConfig.Gateway.RAZORPAY: _get_razorpay_credentials,
    PaymentGatewayConfig.Gateway.PAYU: _get_payu_credentials,
}


def family_of(adapter_key: str) -> str:
    """Provider a registered adapter key belongs to (razorpay_upi -> razorpay)."""
    return adapter_key.split("_", 1)[0]


def credentials_configured(gateway: str, site_settings=None) -> bool:
    """
    True when this provider's own credentials are present (never another provider's).

    Pass an unsaved ``site_settings`` to validate values an admin is about to save.
    """
    loader = _CREDENTIAL_LOADERS.get(gateway)
    return bool(loader and all(loader(site_settings)))


def gateway_status(config: PaymentGatewayConfig) -> str:
    if not config.is_enabled:
        return "Disabled"
    if not credentials_configured(config.gateway):
        return "Enabled — credentials missing (not offered)"
    return "Live — primary" if config.is_primary else "Live"


def get_available_gateways() -> dict:
    """Registered adapters checkout may offer now: enabled + credentialed, primary first."""
    configs = PaymentGatewayConfig.objects.filter(is_enabled=True).order_by("-is_primary", "gateway")
    available = {}
    for config in configs:
        if not credentials_configured(config.gateway):
            continue
        for key, adapter in PAYMENT_GATEWAYS.items():
            if family_of(key) == config.gateway:
                available[key] = adapter
    return available


def is_gateway_available(adapter_key: str) -> bool:
    return adapter_key in get_available_gateways()


def cod_available_for(*, state: str, pincode: str) -> bool:
    """Whether cash on delivery may be offered for a delivery address (admin: Site settings)."""
    from core.services import get_site_settings

    site_settings = get_site_settings()
    if not site_settings.cod_enabled:
        return False
    state = (state or "").strip().lower()
    pincode = (pincode or "").strip()
    blocked_states = {line.strip().lower() for line in site_settings.cod_disabled_states.splitlines() if line.strip()}
    if state and state in blocked_states:
        return False
    for rule in (line.strip() for line in site_settings.cod_disabled_pincodes.splitlines()):
        if not rule:
            continue
        if rule.endswith("*"):
            if pincode.startswith(rule[:-1]):
                return False
        elif pincode == rule:
            return False
    return True
