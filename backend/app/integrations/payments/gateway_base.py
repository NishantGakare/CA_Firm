from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal


class PaymentGateway(ABC):
    @abstractmethod
    def create_order(self, *, amount: Decimal, currency: str, receipt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, *, provider_payment_id: str, provider_order_id: str, signature: str | None) -> bool:
        raise NotImplementedError
