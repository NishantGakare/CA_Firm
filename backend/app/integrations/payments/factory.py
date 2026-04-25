from app.integrations.payments.gateway_base import PaymentGateway
from app.integrations.payments.mock_gateway import MockPaymentGateway


def get_payment_gateway() -> PaymentGateway:
    return MockPaymentGateway()
