from __future__ import annotations

import hmac

from sqlalchemy import exists, literal, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sanic import Blueprint, json

from app.errors import ApiError
from app.models import Account, Payment, User, UserRole
from app.rate_limit import enforce_rate_limit
from app.schemas import PaymentWebhookRequest
from app.security import build_webhook_signature
from app.utils import format_money, parse_payload

webhook_blueprint = Blueprint("webhooks", url_prefix="/api/v1/webhooks")


@webhook_blueprint.post("/payments")
async def process_payment_webhook(request):
    enforce_rate_limit(
        request,
        scope="webhooks.payments",
        limit=request.app.ctx.settings.webhook_rate_limit_requests,
        window_seconds=request.app.ctx.settings.webhook_rate_limit_window_seconds,
    )

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
                await session.execute(
                    pg_insert(Account)
                    .values(
                        id=payload.account_id,
                        user_id=payload.user_id,
                        balance=0,
                    )
                    .on_conflict_do_nothing(index_elements=[Account.id])
                )

                inserted_payment = (
                    await session.execute(
                        pg_insert(Payment)
                        .from_select(
                            ["transaction_id", "user_id", "account_id", "amount"],
                            select(
                                literal(payload.transaction_id),
                                literal(payload.user_id),
                                literal(payload.account_id),
                                literal(payload.amount),
                            ).where(
                                exists(
                                    select(Account.id).where(
                                        Account.id == payload.account_id,
                                        Account.user_id == payload.user_id,
                                    )
                                )
                            ),
                        )
                        .on_conflict_do_nothing(index_elements=[Payment.transaction_id])
                        .returning(
                            Payment.transaction_id,
                            Payment.account_id,
                            Payment.amount,
                        )
                    )
                ).first()

                if inserted_payment is None:
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

                    user_exists = await session.scalar(
                        select(User.id).where(User.id == payload.user_id, User.role == UserRole.USER)
                    )
                    if user_exists is None:
                        raise ApiError(status=404, message="User not found")

                    account_owner_id = await session.scalar(
                        select(Account.user_id).where(Account.id == payload.account_id)
                    )
                    if account_owner_id is not None and account_owner_id != payload.user_id:
                        raise ApiError(status=409, message="Account belongs to another user")

                    raise ApiError(status=409, message="Payment could not be processed")

                updated_account = (
                    await session.execute(
                        update(Account)
                        .where(
                            Account.id == payload.account_id,
                            Account.user_id == payload.user_id,
                        )
                        .values(balance=Account.balance + payload.amount)
                        .returning(Account.id, Account.balance)
                    )
                ).first()

                if updated_account is None:
                    raise ApiError(status=409, message="Account belongs to another user")
        except IntegrityError as exc:
            await session.rollback()
            user_exists = await session.scalar(
                select(User.id).where(User.id == payload.user_id, User.role == UserRole.USER)
            )
            if user_exists is None:
                raise ApiError(status=404, message="User not found") from exc
            raise ApiError(status=409, message="Payment could not be processed") from exc

    return json(
        {
            "status": "processed",
            "transaction_id": payload.transaction_id,
            "account_id": updated_account.id,
            "user_id": payload.user_id,
            "amount": format_money(payload.amount),
            "balance": format_money(updated_account.balance),
        },
        status=201,
    )
