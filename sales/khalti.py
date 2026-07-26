"""
Khalti ePayment (KPG-2) API client.

Docs: https://docs.khalti.com/khalti-epayment/
Only two endpoints are needed for the checkout flow:
  - /epayment/initiate/  -> start a payment, get a redirect payment_url
  - /epayment/lookup/    -> verify the final status of a payment (source of truth)
"""
import requests
from django.conf import settings


class KhaltiError(Exception):
    """Raised when Khalti returns an error response or the request fails."""
    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail


def _headers():
    return {
        'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


def initiate_payment(amount_paisa, purchase_order_id, purchase_order_name,
                      return_url, website_url, customer_info=None):
    """
    Start a Khalti payment. amount_paisa must be an integer (Rs * 100).
    Returns dict with pidx, payment_url, expires_at, expires_in.
    """
    payload = {
        'return_url': return_url,
        'website_url': website_url,
        'amount': int(amount_paisa),
        'purchase_order_id': str(purchase_order_id),
        'purchase_order_name': purchase_order_name,
    }
    if customer_info:
        payload['customer_info'] = customer_info

    try:
        resp = requests.post(
            f'{settings.KHALTI_BASE_URL}/epayment/initiate/',
            json=payload, headers=_headers(), timeout=15,
        )
    except requests.RequestException as exc:
        raise KhaltiError(f'Could not reach Khalti: {exc}')

    data = resp.json()
    if resp.status_code != 200:
        raise KhaltiError('Khalti initiate failed', detail=data)
    return data


def lookup_payment(pidx):
    """
    Verify the current status of a payment by pidx.
    Returns dict with pidx, total_amount, status, transaction_id, fee, refunded.
    Always trust this over the return_url query params.
    """
    try:
        resp = requests.post(
            f'{settings.KHALTI_BASE_URL}/epayment/lookup/',
            json={'pidx': pidx}, headers=_headers(), timeout=15,
        )
    except requests.RequestException as exc:
        raise KhaltiError(f'Could not reach Khalti: {exc}')

    data = resp.json()
    if resp.status_code not in (200, 400):
        raise KhaltiError('Khalti lookup failed', detail=data)
    return data
