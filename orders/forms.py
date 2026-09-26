"""Forms for the orders app."""

from __future__ import annotations

from django import forms


class TrackOrderForm(forms.Form):
    order_number = forms.CharField(max_length=40, label="Order number")
    email = forms.EmailField(label="Email used on the order")
