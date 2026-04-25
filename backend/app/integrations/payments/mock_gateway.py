from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.integrations.payments.gateway_base import PaymentGateway


class MockPaymentGateway(PaymentGateway):
    def create_order(self, *, amount: Decimal, currency: str, receipt: str) -> str:
        return f"mock_order_{uuid4().hex[:20]}"

    def verify(self, *, provider_payment_id: str, provider_order_id: str, signature: str | None) -> bool:
        # For local prototype: any non-empty payment/order IDs are accepted.
        return bool(provider_payment_id and provider_order_id)
