from __future__ import annotations

import hmac

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sanic import Blueprint, json

from app.errors import ApiError
from app.models import Account, Payment, User, UserRole
from app.schemas import PaymentWebhookRequest
from app.security import build_webhook_signature
from app.utils import format_money, parse_payload

webhook_blueprint = Blueprint("webhooks", url_prefix="/api/v1/webhooks")


@webhook_blueprint.post("/payments")
async def process_payment_webhook(request):
    raw_payload = request.json
    if not isinstance(raw_payload, dict):
        raise ApiError(status=400, message="Request body must be a JSON object")

    payload = parse_payload(PaymentWebhookRequest, raw_payload)
    expected_signature = build_webhook_signature(raw_payload, request.app.ctx.settings.payment_secret_key)

    if not hmac.compare_digest(payload.signature, expected_signature):
        raise ApiError(status=400, message="Invalid signature")

    async with request.app.ctx.session_factory() as session:
        try:
            async with session.begin():
                user = await session.scalar(
                    select(User).where(User.id == payload.user_id, User.role == UserRole.USER)
                )
                if user is None:
                    raise ApiError(status=404, message="User not found")

                existing_payment = await session.scalar(
                    select(Payment).where(Payment.transaction_id == payload.transaction_id)
                )
                if existing_payment is not None:
                    return json(
                        {
                            "status": "duplicate",
                            "transaction_id": existing_payment.transaction_id,
                            "account_id": existing_payment.account_id,
                            "amount": format_money(existing_payment.amount),
                        }
                    )

                statement = (
                    pg_insert(Account)
                    .values(
                        id=payload.account_id,
                        user_id=payload.user_id,
                        balance=0,
                    )
                    .on_conflict_do_nothing(index_elements=[Account.id])
                )
                await session.execute(statement)

                account = await session.scalar(
                    select(Account).where(Account.id == payload.account_id).with_for_update()
                )
                if account is None:
                    raise ApiError(status=500, message="Failed to load or create account")

                if account.user_id != payload.user_id:
                    raise ApiError(status=409, message="Account belongs to another user")

                payment = Payment(
                    transaction_id=payload.transaction_id,
                    user_id=payload.user_id,
                    account_id=payload.account_id,
                    amount=payload.amount,
                )
                session.add(payment)
                account.balance = account.balance + payload.amount
        except IntegrityError as exc:
            await session.rollback()
            duplicate_payment = await session.scalar(
                select(Payment).where(Payment.transaction_id == payload.transaction_id)
            )
            if duplicate_payment is not None:
                return json(
                    {
                        "status": "duplicate",
                        "transaction_id": duplicate_payment.transaction_id,
                        "account_id": duplicate_payment.account_id,
                        "amount": format_money(duplicate_payment.amount),
                    }
                )
            raise ApiError(status=409, message="Payment could not be processed") from exc

    return json(
        {
            "status": "processed",
            "transaction_id": payload.transaction_id,
            "account_id": account.id,
            "user_id": payload.user_id,
            "amount": format_money(payload.amount),
            "balance": format_money(account.balance),
        },
        status=201,
    )
