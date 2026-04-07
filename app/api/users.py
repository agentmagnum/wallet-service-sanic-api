from __future__ import annotations

from sqlalchemy import select
from sanic import Blueprint, json

from app.models import Account, Payment, UserRole
from app.pagination import parse_pagination
from app.security import require_roles
from app.utils import format_money, isoformat_or_none

user_blueprint = Blueprint("users", url_prefix="/api/v1")


@user_blueprint.get("/me")
@require_roles(UserRole.USER, UserRole.ADMIN)
async def get_me(request):
    return json(request.ctx.current_user.to_dict())


@user_blueprint.get("/accounts")
@require_roles(UserRole.USER)
async def list_accounts(request):
    async with request.app.ctx.session_factory() as session:
        query = (
            select(Account)
            .where(Account.user_id == request.ctx.current_user.user_id)
            .order_by(Account.id.asc())
        )
        accounts = list(await session.scalars(query))

    return json(
        {
            "items": [
                {
                    "id": account.id,
                    "balance": format_money(account.balance),
                    "created_at": isoformat_or_none(account.created_at),
                }
                for account in accounts
            ]
        }
    )


@user_blueprint.get("/payments")
@require_roles(UserRole.USER)
async def list_payments(request):
    pagination = parse_pagination(request, default_limit=100, max_limit=500)

    async with request.app.ctx.session_factory() as session:
        query = (
            select(Payment)
            .where(Payment.user_id == request.ctx.current_user.user_id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
        )
        if pagination.limit is not None:
            query = query.offset(pagination.offset).limit(pagination.limit)
        payments = list(await session.scalars(query))

    return json(
        {
            "items": [
                {
                    "id": payment.id,
                    "transaction_id": payment.transaction_id,
                    "account_id": payment.account_id,
                    "amount": format_money(payment.amount),
                    "created_at": isoformat_or_none(payment.created_at),
                }
                for payment in payments
            ],
            "pagination": pagination.to_meta(returned_count=len(payments)),
        }
    )
